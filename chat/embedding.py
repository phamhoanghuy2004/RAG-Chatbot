import redis
import uuid
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient,models
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.storage import RedisStore
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.schema.document import Document
from django.conf import settings

from langchain_community.retrievers import TFIDFRetriever
from langchain.retrievers import EnsembleRetriever
from qdrant_client.http.models import PayloadSchemaType

# Tạo embedding model tối ưu cho tiếng Việt
embedding_model = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
collection_name = settings.COLLECTION_NAME

# Qdrant client
qdrant_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

#Valkey client
valkey_client = redis.from_url(settings.VALKEY_URL, decode_responses=True)

# Cache for TF-IDF retrievers per source
tfidf_cache = {}


def create_tfidf_retriever(source, contexts, k=3):
    """Create and cache TF-IDF retriever for a specific source"""
    cache_key = f"tfidf_{source}"
    
    if cache_key not in tfidf_cache:
        # Create documents for TF-IDF
        tfidf_docs = [Document(page_content=context, metadata={"source": source}) for context in contexts]
        
        # Create TF-IDF retriever
        tfidf_retriever = TFIDFRetriever.from_documents(tfidf_docs, k=k)
        tfidf_cache[cache_key] = tfidf_retriever
        print(f"Created new TF-IDF retriever for source: {source}")
    
    return tfidf_cache[cache_key]


def get_contexts_for_tfidf(source):
    """Retrieve stored contexts from Redis for TF-IDF indexing"""
    doc_store = RedisStore(client=valkey_client)
    
    # Get all doc_ids for the source from Qdrant
    filter_conditions = Filter(
        must=[
            FieldCondition(
                key="metadata.source",
                match=MatchValue(value=source)
            )
        ]
    )
    
    all_points = []
    scroll_offset = None
    
    while True:
        points, scroll_offset = qdrant_client.scroll(
            collection_name=collection_name,
            scroll_filter=filter_conditions,
            limit=100,
            offset=scroll_offset,
            with_payload=["metadata.doc_id"]
        )
        
        if not points:
            break
            
        all_points.extend(points)
        
        if scroll_offset is None:
            break
    
    # Get doc_ids and retrieve contexts from Redis
    doc_ids = [point.payload["metadata"]["doc_id"] for point in all_points if "metadata" in point.payload and "doc_id" in point.payload["metadata"]]
    
    contexts = []
    for doc_id in doc_ids:
        try:
            # Use mget for batch retrieval, but since RedisStore doesn't have get method,
            # let's access the underlying Redis client directly
            context = valkey_client.get(doc_id)
            if context:
                contexts.append(context)
        except Exception as e:
            print(f"Error retrieving context for doc_id {doc_id}: {e}")
            continue
    
    return contexts


def create_hybrid_retriever(source, id_key="doc_id", k=3, weights=[0.7, 0.3]):  # Increased default k
    """
    Create a hybrid retriever combining dense (multivector) and sparse (TF-IDF) retrieval
    
    Args:
        source: Document source identifier
        id_key: Key for document IDs
        k: Number of documents to retrieve
        weights: [dense_weight, sparse_weight] - should sum to 1.0
    
    Returns:
        EnsembleRetriever combining both approaches
    """
    # Create multivector retriever (dense)
    dense_retriever = create_retriever_multivector(source, id_key, k)
    
    # Get contexts for TF-IDF
    contexts = get_contexts_for_tfidf(source)
    
    if not contexts:
        print(f"No contexts found for source: {source}. Falling back to dense retriever only.")
        return dense_retriever
    
    # Create TF-IDF retriever (sparse)
    sparse_retriever = create_tfidf_retriever(source, contexts, k)
    
    # Create ensemble retriever
    hybrid_retriever = EnsembleRetriever(
        retrievers=[dense_retriever, sparse_retriever],
        weights=weights
    )
    
    print(f"Created hybrid retriever for source: {source} with weights: {weights}")
    return hybrid_retriever


def clear_tfidf_cache(source=None):
    """Clear TF-IDF cache for a specific source or all sources"""
    global tfidf_cache
    
    if source:
        cache_key = f"tfidf_{source}"
        if cache_key in tfidf_cache:
            del tfidf_cache[cache_key]
            print(f"Cleared TF-IDF cache for source: {source}")
    else:
        tfidf_cache.clear()
        print("Cleared all TF-IDF cache")


def check_collection():
    collections = qdrant_client.get_collections().collections

    # Nếu chưa có collection thì tạo
    if not any(c.name == collection_name for c in collections):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=768,
                distance=models.Distance.COSINE
            )
        )

    # Ensure payload indexes
    qdrant_client.create_payload_index(
        collection_name=collection_name,
        field_name="metadata.source",
        field_schema=PayloadSchemaType.KEYWORD
    )

    qdrant_client.create_payload_index(
        collection_name=collection_name,
        field_name="metadata.doc_id",
        field_schema=PayloadSchemaType.KEYWORD
    )
        
def create_retriever_multivector (source, id_key = "doc_id", k = 3):  # Increased default k
    check_collection ()
    
    vector_store = QdrantVectorStore (
        client=qdrant_client,
        collection_name=collection_name,
        embedding=embedding_model
    )
    
    doc_store = RedisStore(client=valkey_client)
    
    filter_conditions = Filter(
        must = [
            FieldCondition (
                key="metadata.source",
                match=MatchValue(value=source)
            )
        ]
    )
    
    search_kwargs = {}
    if filter_conditions:
        search_kwargs = {
            "filter" : filter_conditions,
            "k" : k  # Use the k parameter instead of hardcoded 3
        }
    
    retriever = MultiVectorRetriever (
        vectorstore=vector_store,
        docstore=doc_store,
        id_key=id_key,
        search_kwargs=search_kwargs
    )
    
    return retriever
    

def embedding_multivector (contexts , summaries, name_software, version_software):
    print(f"DEBUG: Embedding multivector for {name_software}, {len(contexts)} contexts")
    id_key = "doc_id"
    retriever = create_retriever_multivector(name_software, id_key , 3)
    doc_ids = [str(uuid.uuid4()) for _ in contexts]
    sum_docs = [
        Document( page_content=summary, metadata={id_key: doc_ids[i], "source":name_software, "version":version_software} )
        for i, summary in enumerate (summaries)
    ]
    
    retriever.vectorstore.add_documents(sum_docs)
    retriever.docstore.mset(list(zip(doc_ids,contexts)))    
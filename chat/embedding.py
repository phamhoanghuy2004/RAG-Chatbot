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

# Tạo embedding model tối ưu cho tiếng Việt
embedding_model = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
collection_name = settings.COLLECTION_NAME

# Qdrant client
qdrant_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

#Valkey client
valkey_client = redis.from_url(settings.VALKEY_URL, decode_responses=True)


def check_collection ():
    # Nếu collection chưa có thì tạo
    collections = qdrant_client.get_collections().collections
    if not any(c.name == collection_name for c in collections): 
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
        )
    

def create_retriever_multivector (source, id_key = "doc_id", k = 3):
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
            "k" : 3
        }
    
    retriever = MultiVectorRetriever (
        vectorstore=vector_store,
        docstore=doc_store,
        id_key=id_key,
        search_kwargs=search_kwargs
    )
    
    return retriever
    

def embedding_multivector (contexts , summaries, name_software, version_software):
    id_key = "doc_id"
    retriever = create_retriever_multivector(name_software, id_key , 3)
    doc_ids = [str(uuid.uuid4()) for _ in contexts]
    sum_docs = [
        Document( page_content=summary, metadata={id_key: doc_ids[i], "source":name_software, "version":version_software} )
        for i, summary in enumerate (summaries)
    ]
    
    retriever.vectorstore.add_documents(sum_docs)
    retriever.docstore.mset(list(zip(doc_ids,contexts)))    
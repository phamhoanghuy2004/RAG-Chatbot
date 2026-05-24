import redis
import uuid
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
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

# Valkey client
valkey_client = redis.from_url(settings.VALKEY_URL, decode_responses=True)

# Cache for TF-IDF retrievers — key = frozenset of sources
tfidf_cache = {}


def _normalize_sources(sources) -> list:
    """
    Chuẩn hóa tham số sources về dạng list[str].
    Chấp nhận: str đơn, list, hoặc tuple.
    """
    if isinstance(sources, str):
        return [sources]
    return list(sources)


# ---------------------------------------------------------------------------
# TF-IDF helpers
# ---------------------------------------------------------------------------

def get_contexts_for_tfidf(sources) -> list:
    """
    Lấy toàn bộ text chunk từ Redis cho một hoặc nhiều source.

    Args:
        sources: str | list[str] — tên nguồn tài liệu (không có .pdf)

    Returns:
        list[str] — danh sách các text chunk
    """
    sources = _normalize_sources(sources)

    # Xây filter OR trên nhiều source
    if len(sources) == 1:
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="metadata.source",
                    match=MatchValue(value=sources[0])
                )
            ]
        )
    else:
        filter_conditions = Filter(
            should=[
                FieldCondition(
                    key="metadata.source",
                    match=MatchValue(value=s)
                )
                for s in sources
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

    doc_ids = [
        point.payload["metadata"]["doc_id"]
        for point in all_points
        if "metadata" in point.payload and "doc_id" in point.payload["metadata"]
    ]

    contexts = []
    for doc_id in doc_ids:
        try:
            context = valkey_client.get(doc_id)
            if context:
                contexts.append(context)
        except Exception as e:
            print(f"Error retrieving context for doc_id {doc_id}: {e}")
            continue

    return contexts


def create_tfidf_retriever(sources, contexts, k=3):
    """
    Tạo và cache TF-IDF retriever cho một hoặc nhiều source.

    Args:
        sources: str | list[str]
        contexts: list[str] — các text chunk tương ứng
        k: số kết quả trả về

    Returns:
        TFIDFRetriever
    """
    sources = _normalize_sources(sources)
    cache_key = "tfidf_" + "|".join(sorted(sources))

    if cache_key not in tfidf_cache:
        tfidf_docs = [
            Document(page_content=ctx, metadata={"source": "|".join(sources)})
            for ctx in contexts
        ]
        tfidf_retriever = TFIDFRetriever.from_documents(tfidf_docs, k=k)
        tfidf_cache[cache_key] = tfidf_retriever
        print(f"Created new TF-IDF retriever for sources: {sources}")

    return tfidf_cache[cache_key]


# ---------------------------------------------------------------------------
# Dense (multivector) retriever
# ---------------------------------------------------------------------------

def check_collection():
    collections = qdrant_client.get_collections().collections

    if not any(c.name == collection_name for c in collections):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=768,
                distance=models.Distance.COSINE
            )
        )

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


def create_retriever_multivector(sources, id_key="doc_id", k=3):
    """
    Tạo MultiVectorRetriever lọc theo một hoặc nhiều source.

    Args:
        sources: str | list[str]
        id_key: trường ID trong metadata
        k: số kết quả trả về

    Returns:
        MultiVectorRetriever
    """
    sources = _normalize_sources(sources)
    check_collection()

    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=collection_name,
        embedding=embedding_model
    )

    doc_store = RedisStore(client=valkey_client)

    # Xây filter OR nếu nhiều source
    if len(sources) == 1:
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="metadata.source",
                    match=MatchValue(value=sources[0])
                )
            ]
        )
    else:
        filter_conditions = Filter(
            should=[
                FieldCondition(
                    key="metadata.source",
                    match=MatchValue(value=s)
                )
                for s in sources
            ]
        )

    search_kwargs = {
        "filter": filter_conditions,
        "k": k
    }

    retriever = MultiVectorRetriever(
        vectorstore=vector_store,
        docstore=doc_store,
        id_key=id_key,
        search_kwargs=search_kwargs
    )

    return retriever


# ---------------------------------------------------------------------------
# Hybrid retriever
# ---------------------------------------------------------------------------

def create_hybrid_retriever(sources, id_key="doc_id", k=3, weights=None):
    """
    Tạo hybrid retriever kết hợp dense (multivector) và sparse (TF-IDF)
    cho một hoặc nhiều source.

    Args:
        sources: str | list[str] — tên tài liệu (không có .pdf)
        id_key: trường ID
        k: số kết quả
        weights: [dense_weight, sparse_weight], mặc định [0.7, 0.3]

    Returns:
        EnsembleRetriever hoặc MultiVectorRetriever (fallback)
    """
    if weights is None:
        weights = [0.7, 0.3]

    sources = _normalize_sources(sources)

    # Dense retriever
    dense_retriever = create_retriever_multivector(sources, id_key, k)

    # Sparse retriever
    contexts = get_contexts_for_tfidf(sources)

    if not contexts:
        print(f"No contexts found for sources: {sources}. Falling back to dense retriever only.")
        return dense_retriever

    sparse_retriever = create_tfidf_retriever(sources, contexts, k)

    hybrid_retriever = EnsembleRetriever(
        retrievers=[dense_retriever, sparse_retriever],
        weights=weights
    )

    print(f"Created hybrid retriever for sources: {sources} with weights: {weights}")
    return hybrid_retriever


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def clear_tfidf_cache(sources=None):
    """
    Xóa cache TF-IDF cho một hoặc nhiều source, hoặc toàn bộ.

    Args:
        sources: str | list[str] | None — None để xóa hết
    """
    global tfidf_cache

    if sources is None:
        tfidf_cache.clear()
        print("Cleared all TF-IDF cache")
    else:
        sources = _normalize_sources(sources)
        cache_key = "tfidf_" + "|".join(sorted(sources))
        if cache_key in tfidf_cache:
            del tfidf_cache[cache_key]
            print(f"Cleared TF-IDF cache for sources: {sources}")


# ---------------------------------------------------------------------------
# Embedding (không đổi logic, chỉ gọi single-source)
# ---------------------------------------------------------------------------

def embedding_multivector(contexts, summaries, name_software, version_software):
    print(f"DEBUG: Embedding multivector for {name_software}, {len(contexts)} contexts")
    id_key = "doc_id"
    # embedding luôn là single source khi ingest
    retriever = create_retriever_multivector(name_software, id_key, 3)
    doc_ids = [str(uuid.uuid4()) for _ in contexts]
    sum_docs = [
        Document(
            page_content=summary,
            metadata={id_key: doc_ids[i], "source": name_software, "version": version_software}
        )
        for i, summary in enumerate(summaries)
    ]

    retriever.vectorstore.add_documents(sum_docs)
    retriever.docstore.mset(list(zip(doc_ids, contexts)))
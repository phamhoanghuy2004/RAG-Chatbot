import os
import traceback
from . import model_response
from . import embedding


# Danh sách các model (chỉ hỗ trợ LLaMA)
model_dispatch = {
    "llama-3.1-8b-instant": model_response.response_of_llama3_instant,
    "llama-3.3-70b-versatile": model_response.response_of_llama3_70b,
}

# def get_context_with_multivector (question : str, source):
#     retriever = embedding.create_retriever_multivector (source, id_key = "doc_id", k = 3)  # Increased k from 3 to 5
#     contexts =  retriever.invoke(question)
#     # Enhanced context formatting to preserve more information
#     cleaned_contexts = "\n\n" + "="*80 + "\n\n".join([
#         f"📄 DOCUMENT CHUNK {i+1}:\n{str(context)}" 
#         for i, context in enumerate(contexts)
#     ]) + "\n\n" + "="*80
#     return cleaned_contexts


def get_context_with_hybrid_retriever(question: str, sources, weights=[0.7, 0.3]):
    """
    Retrieve context using hybrid retriever (dense + sparse) for one or multiple sources.

    Args:
        question: User query
        sources: str | list[str] — tên tài liệu (không có .pdf)
        weights: [dense_weight, sparse_weight]

    Returns:
        Cleaned context string
    """
    try:
        retriever = embedding.create_hybrid_retriever(sources, id_key="doc_id", k=2, weights=weights)
        label = sources if isinstance(sources, str) else ", ".join(sources)
        print(f"Using hybrid retriever for sources: {label}")

        contexts = retriever.invoke(question)
        cleaned_contexts = "\n\n" + "="*80 + "\n\n".join([
            f"&&  DOCUMENT CHUNK {i+1}:\n{str(context)}"
            for i, context in enumerate(contexts)
        ]) + "\n\n" + "="*80
        return cleaned_contexts

    except Exception as e:
        print(f"Error in hybrid retrieval, falling back: {str(e)}")
        return None

def query_with_rag_use_qdrant(question: str, sources, model: str, hybrid_weights: list = [0.7, 0.3]) -> str:
    """
    Thực thi RAG pipeline.

    Args:
        question: câu hỏi của người dùng
        sources: str | list[str] — tên tài liệu không có .pdf
                 Ví dụ: "TaiLieuA" hoặc ["TaiLieuA", "TaiLieuB"]
        model: tên model LLM
        hybrid_weights: trọng số [dense, sparse]
    """
    # Chặn luồng nếu sources rỗng — KHÔNG gọi Qdrant, KHÔNG gọi LLM
    if not sources or sources == "" or (isinstance(sources, list) and len(sources) == 0):
        return "Xin chào, Bạn vui lòng chọn tài liệu ở trên để mình hướng dẫn nhé!"

    if not model:
        return "Xin chào, Bạn vui lòng chọn model nào để xem kết quả phản hồi nhé!"

    if not question:
        return "Xin chào, Bạn vui lòng cho mình biết bạn muốn hỏi gì nhé!"

    try:
        contexts = get_context_with_hybrid_retriever(question, sources, weights=hybrid_weights)
        excerpts = contexts if contexts else "Không tìm thấy thông tin phù hợp từ PDF"
    except Exception as e:
        excerpts = "Không tìm thấy dữ liệu phù hợp từ PDF."
        print("[WARN] Không tìm thấy dữ liệu từ PDF.")
        print("Loại lỗi:", type(e).__name__)
        print("Chi tiết:", str(e))
        traceback.print_exc()

    response_fn = model_dispatch.get(model)
    if response_fn:
        return response_fn(question, excerpts)
    else:
        return f"⚠️ Model '{model}' chưa được hỗ trợ."

def print_debug (retrieves_docs,filtered_chunk):   
    print("\n📌 [STEP 1] Các chunk được Qdrant truy xuất (top 5):\n")
    for i, doc in enumerate(retrieves_docs, 1):
        print(f"--- Retrieved Chunk {i} ---")
        print(doc.page_content.strip())
        print("-" * 60)

    print("\n📌 [STEP 2] Các chunk được giữ lại sau khi lọc bằng m3e-base (theo threshold):\n")
    
    if not filtered_chunk:
        print("❌ Không có chunk nào được giữ lại sau lọc.")
    else:
        for i, (chunk, score) in enumerate(filtered_chunk, 1):
            print(f"✅ Filtered Chunk {i} | Similarity: {score:.3f}")
            print(chunk.strip())
            print("-" * 60)

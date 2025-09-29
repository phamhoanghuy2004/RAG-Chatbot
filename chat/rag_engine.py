import os
import traceback
from . import model_response
from . import embedding


# Danh sách các model
model_dispatch = {
    "gemma2-9b-it": model_response.response_of_gemma2,
    "llama-3.1-8b-instant": model_response.response_of_llama3_instant,
    "llama-3.3-70b-versatile": model_response.response_of_llama3_70b,
}

def get_context_with_multivector (question : str, source):
    retriever = embedding.create_retriever_multivector (source, id_key = "doc_id", k = 5)  # Increased k from 3 to 5
    contexts =  retriever.invoke(question)
    # Enhanced context formatting to preserve more information
    cleaned_contexts = "\n\n" + "="*80 + "\n\n".join([
        f"📄 DOCUMENT CHUNK {i+1}:\n{str(context)}" 
        for i, context in enumerate(contexts)
    ]) + "\n\n" + "="*80
    return cleaned_contexts


def get_context_with_hybrid_retriever(question: str, source, use_hybrid=True, weights=[0.7, 0.3]):
    """
    Retrieve context using hybrid retriever (dense + sparse) or fallback to multivector only
    
    Args:
        question: User query
        source: Document source
        use_hybrid: Whether to use hybrid retrieval or just dense
        weights: [dense_weight, sparse_weight] for hybrid retrieval
    
    Returns:
        Cleaned context string
    """
    try:
        if use_hybrid:
            retriever = embedding.create_hybrid_retriever(source, id_key="doc_id", k=5, weights=weights)  # Increased k
            print(f"Using hybrid retriever for source: {source}")
        else:
            retriever = embedding.create_retriever_multivector(source, id_key="doc_id", k=5)  # Increased k
            print(f"Using dense-only retriever for source: {source}")
            
        contexts = retriever.invoke(question)
        # Enhanced context formatting to preserve more information
        cleaned_contexts = "\n\n" + "="*80 + "\n\n".join([
            f"📄 DOCUMENT CHUNK {i+1}:\n{str(context)}" 
            for i, context in enumerate(contexts)
        ]) + "\n\n" + "="*80
        return cleaned_contexts
        
    except Exception as e:
        print(f"Error in hybrid retrieval, falling back to multivector: {str(e)}")
        # Fallback to original multivector approach
        return get_context_with_multivector(question, source)

def query_with_rag_use_qdrant (question: str, source: str, model: str, use_hybrid: bool = False, hybrid_weights: list = [0.7, 0.3]) ->str:
    
    if source == "" or not source:
        return "Xin chào, Bạn vui lòng chọn tài liệu ở trên để mình hướng dẫn nhé!"
    
    if model == "" or not model:
        return "Xin chào, Bạn vui lòng chọn model nào để xem kết quả phản hồi nhé!"
    
    if question == "" or not question:
        return "Xin chào, Bạn vui lòng cho mình biết bạn muốn hỏi gì nhé!"
    
    try: 
        # get context using hybrid or multivector retriever
        if use_hybrid:
            contexts = get_context_with_hybrid_retriever(question, source, use_hybrid=True, weights=hybrid_weights)
        else:
            contexts = get_context_with_multivector(question, source)   
        
        # if not context
        if not contexts :
            excerpts = "Không tìm thấy thông tin phù hợp từ PDF"
        else:
            excerpts  = contexts
                         
    except Exception as e:
        excerpts = "Không tìm thấy dữ liệu phù hợp từ PDF."
        print("[WARN] Không tìm thấy dữ liệu từ PDF.")
        print("Loại lỗi:", type(e).__name__)
        print("Chi tiết:", str(e))
        traceback.print_exc()
        
    response_fn = model_dispatch.get(model)
    if (response_fn):
        return response_fn (question,excerpts)
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

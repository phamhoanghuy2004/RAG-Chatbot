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
    retriever = embedding.create_retriever_multivector (source, id_key = "doc_id", k = 3)
    contexts =  retriever.invoke(question)
    cleaned_contexts = "\n\n---\n\n".join([str(context) for context in contexts])
    return cleaned_contexts

def query_with_rag_use_qdrant (question: str, source: str, model: str) ->str:
    
    if source == "" or not source:
        return "Xin chào, Bạn vui lòng chọn tài liệu ở trên để mình hướng dẫn nhé!"
    
    if model == "" or not model:
        return "Xin chào, Bạn vui lòng chọn model nào để xem kết quả phản hồi nhé!"
    
    if question == "" or not question:
        return "Xin chào, Bạn vui lòng cho mình biết bạn muốn hỏi gì nhé!"
    
    try: 
        # get context 
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

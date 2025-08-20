from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate
from django.conf import settings



def _generic_response(question, excerpts, model_name, assistant_name):
           
    prompt = PromptTemplate.from_template("""
        Bạn là {assistant_name} một trợ lý kỹ thuật thông minh, chuyên hỗ trợ người dùng sử dụng phần mềm.

        Dựa trên thông tin ngữ cảnh dưới đây, hãy trả lời câu hỏi một cách chính xác và dễ hiểu. Khi đề cập đến hình ảnh, hãy sử dụng định dạng thẻ <img> giống như trong ngữ cảnh (ví dụ: <img src='đường_dẫn' alt='mô_tả' class='pictureResponse' />) để hiển thị hình ảnh. Nếu không tìm thấy câu trả lời trong ngữ cảnh, hãy trả lời: "Tôi không có đủ thông tin để trả lời câu hỏi này."

        Ngữ cảnh:
        {context}

        Câu hỏi:
        {question}
        
        Lưu ý: Hãy luôn giới thiệu bạn là {assistant_name} ở đầu câu trả lời.
        
    """).format(
        assistant_name = assistant_name,
        question = question,
        context = excerpts
    )
    
    print("=======================Prompt============================")
    print(prompt)
    print("========================================================= ")
    
    try:
        llm = ChatOpenAI (
            model = model_name,
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )
        message = [HumanMessage(content=prompt)]
        response = llm.invoke(message)
        return response.content or "Không có phản hồi Model"
    except Exception as ex:
        return f"Lỗi gọi LLM: {str(ex)}"
    
def response_of_gemma2 (question, excerpts):
    return _generic_response(
        question, excerpts,
        model_name="gemma2-9b-it",
        assistant_name="Trợ lý RAG dùng Gemma 2 9B"
    )


def response_of_llama3_instant (question, excerpts):
    return _generic_response(
        question, excerpts,
        model_name="llama-3.1-8b-instant",
        assistant_name="Trợ lý LLaMA 3.1 8B Instant"
    )


def response_of_llama3_70b (question, excerpts):
    return _generic_response(
        question, excerpts,
        model_name="llama-3.3-70b-versatile",
        assistant_name="Trợ lý LLaMA 3.3 70B Versatile"
    )

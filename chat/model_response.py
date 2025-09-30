from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate
from django.conf import settings

from . import database_util

def _generic_response(question, excerpts, model_name, assistant_name):
    
    strPrompt = database_util.get_generate_prompt()
    if not strPrompt:
        return "Xin lỗi tôi chưa thể trả lời câu hỏi của bạn. Do tôi bị lỗi liên quan đến prompt"
           
    prompt = PromptTemplate.from_template(strPrompt.content).format(
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

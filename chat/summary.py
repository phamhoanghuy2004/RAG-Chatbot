from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
from django.conf import settings


def create_summarize_chain (model_name = "llama-3.1-8b-instant", temperature=0.5):
    
    prompt_text = """
        Bạn là một trợ lý ngôn ngữ chuyên rút trích thông tin cho hệ thống RAG. 
        Nhiệm vụ của bạn là đọc kỹ đoạn văn sau và tạo một bản tóm tắt ngắn gọn, súc tích, chứa các ý chính quan trọng nhất, đảm bảo chunk tóm tắt không vượt quá 512 token. 
        Chỉ xuất ra nội dung tóm tắt, không thêm lời giải thích hay nhận xét. 
        Không bắt đầu hoặc kết thúc bằng các cụm từ như “Tóm tắt:” hay “Dưới đây là…”. 
        Đoạn văn cần tóm tắt: {element}  
    """

    prompt = ChatPromptTemplate.from_template(prompt_text)
    model = ChatGroq(temperature=temperature, model=model_name, api_key=settings.GROQ_API_KEY) 
    summarize_chain = {"element": lambda x : x} | prompt | model | StrOutputParser()
    return summarize_chain
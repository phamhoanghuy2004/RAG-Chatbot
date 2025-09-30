from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.prompts import PromptTemplate
from django.conf import settings

from . import database_util

import re

def ensure_images_in_response(response, context):
    """
    Post-process response to log missing images but don't add them automatically
    
    Args:
        response: Generated response text
        context: Original context used for generation
        
    Returns:
        Original response without automatic image additions
    """
    # Find all images in context
    context_images = re.findall(r'<img[^>]*>', context)
    
    # Find all images in response
    response_images = re.findall(r'<img[^>]*>', response)
    
    # Find missing images
    missing_images = []
    for img in context_images:
        if img not in response:
            missing_images.append(img)
    
    # Just log missing images for debugging, don't add them
    if missing_images:
        print(f"[IMAGE INFO] {len(missing_images)} images from context not included in response")
    else:
        print(f"[IMAGE INFO] All {len(context_images)} context images included in response")
    
    return response


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
            temperature=0.7,  # Increased for more detailed and nuanced responses
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            max_tokens=2048,  # Ensure longer responses for comprehensive answers
            top_p=0.9  # Allow for more diverse token selection
        )
        message = [HumanMessage(content=prompt)]
        response = llm.invoke(message)
        return response.content or "Không có phản hồi Model"
        # raw_response = response.content or "Không có phản hồi Model"
        
        # # Post-process to ensure images are included
        # enhanced_response = ensure_images_in_response(raw_response, excerpts)
        # return enhanced_response
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

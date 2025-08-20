from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import json
import os
from . import rag_engine
from . import util
from . import ingest_pdf
from django.http import StreamingHttpResponse
from threading import Thread
import queue

from .models import LogEntry
import time

@csrf_exempt
def compare_models_result (request):
    if (request.method == 'POST'):
        data = json.loads(request.body)
        question = data.get('question',"")
        source = data.get('source',"")
        parts = source.split("_")
        if len(parts) > 2:
            name_software = parts[1]
        else:
            name_software = None
        model1 = data.get('model1',"")
        model2 = data.get('model2',"")
        
        result_queue = queue.Queue()
        
        def run_model(model_name):
            try:
                result = rag_engine.query_with_rag_use_qdrant(question,name_software,model_name)
            except Exception as e:
                result = f"Lỗi gọi model {model_name}: {str(e)}"    
            result_queue.put(result)
            
        # Tạo thread chạy xong xong hai model
        Thread(target=run_model, args=(model1,), daemon=True).start()
        Thread(target=run_model, args=(model2,), daemon=True).start()
        
        def stream():
            received = 0
            while received < 2:
                result = result_queue.get()
                tag = "model1" if received == 0 else "model2"
                yield f"###BEGIN_{tag}###\n{result}\n###END_{tag}###\n"
                received += 1
        return StreamingHttpResponse(stream(), content_type="text/event-stream")
    
    return StreamingHttpResponse("Error", content_type="text/plain")
        

def chat_page (request):
    # Lấy tất cả các file pdf đang có trong thư mục
    docs_dir = os.path.join(settings.BASE_DIR,'docs')
    docs  = util.get_valid_pdf_files(docs_dir)
    return render(request,'chat.html',context={'docs' : docs})

@csrf_exempt
def upload_pdf (request):
    if request.method == 'POST' and request.FILES.get('pdf'):
        pdf = request.FILES['pdf']
        if not util.is_valid_pdf_name (pdf.name):
            return JsonResponse({"error": "Invalid file name"}, status=400)
        
        name_software, version_software = util.extract_software_name(pdf.name)
        if not name_software or not version_software:
            return JsonResponse({"error": "Invalid file name"}, status=400)
        
        # update point, docs và delete existing file
        docs_dir = os.path.join(settings.BASE_DIR,'docs')
        images_dir = os.path.join(settings.BASE_DIR, 'extracted_images')
        util.remove_old_software_pdf(docs_dir, pdf.name, name_software, version_software)

        
        #Lưu lại pdf trong thư mục blog/docs
        saved_absolute_path = util.save_pdf_to_storage(pdf, docs_dir)
        
        # Gọi xử lý
        ingest_pdf.ingest_pdf_docling(saved_absolute_path, name_software, version_software, images_dir)
        
        return JsonResponse({'message': 'Tải lên thành công!'})
        
    return JsonResponse({"error" : "Invalid file"},status=400)


@csrf_exempt
def chat(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        question = data.get('question', "")
        source = data.get('source',"")
        model = data.get('model', "")
        parts = source.split("_")
        if len(parts) > 2:
            name_software = parts[1]
        else:
            name_software = None
            
        start_time = time.time()
        answer = rag_engine.query_with_rag_use_qdrant(question,name_software,model)
        latency = round(time.time() - start_time, 2)
        
        # Log the user query and RAG answer
        log = LogEntry.objects.create(
            user_question=question,
            rag_answer=answer,
            accuracy="N/A",  # VD: "100" hoặc "0"
            latency=latency,    # VD: 2.1
            user_satisfaction=0 # VD: 5
        )
        # Sau khi nhận response từ /api/chat/
        print("API /api/chat/ response:", data)
        print("LogEntry created with id:", log.id)
        return JsonResponse({"answer": answer, "log_id": log.id})
    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def feedback(request):
    data = json.loads(request.body)
    log_id = data.get('log_id')
    accuracy = data.get('accuracy')
    user_satisfaction = data.get('user_satisfaction')
    try:
        log = LogEntry.objects.get(id=log_id)
        log.accuracy = f"{accuracy}"
        log.user_satisfaction = user_satisfaction
        log.save()
        return JsonResponse({'status': 'ok'})
    except LogEntry.DoesNotExist:
        return JsonResponse({'error': 'Log not found'}, status=404)

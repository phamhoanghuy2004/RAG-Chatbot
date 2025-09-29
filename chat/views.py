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
from . import database_util
from . import password_encr
from . import jwt_token_util



from .models import LogEntry
import time

@csrf_exempt
def compare_models_result (request):
    if (request.method != 'POST'):
        return StreamingHttpResponse("Error", content_type="Yêu cầu là phương thức POST!")
    
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
    
        

def chat_page (request):
    # Lấy tất cả các file pdf đang có trong thư mục
    docs_dir = os.path.join(settings.BASE_DIR,'docs')
    docs  = util.get_valid_pdf_files(docs_dir)
    return render(request,'chat.html',context={'docs' : docs})

def login_page (request):
    return render(request,'login.html')

@csrf_exempt
def upload_pdf (request):
    if request.method != "POST":
        return JsonResponse({"error" : "Yêu cầu là phương thức POST!"},status=405)
    
    # 1) AuthN/AuthZ
    token = request.COOKIES.get("access_token")
    if not token:
        return JsonResponse({"error": "Không thể thực hiện!"}, status=401)
    
    payload = jwt_token_util.decode_jwt(token)
    if not payload:
        return JsonResponse({"error": "Không thể thực hiện!"}, status=401)
    
    if not payload.get("user_id"):
        return JsonResponse({"error": "Không thể thực hiện!"}, status=401)
    
    if not database_util.get_user_by_id(payload.get("user_id")): 
        return JsonResponse({"error": "Không thể thực hiện!"}, status=401)
    
    if payload.get("role") not in ["admin", "staff"]:
        return JsonResponse({"error": "Không thể thực hiện!"}, status=401)
    
    # 2) Input
    pdf = request.FILES.get('pdf')
    if not pdf:
        return JsonResponse({"error": "File không hợp lệ!"}, status=400)
    
    if not util.is_valid_pdf_name (pdf.name):
        return JsonResponse({"error": "File không hợp lệ!"}, status=400)
    
    # Kiểm tra loại/kích thước file (khuyến nghị)
    if pdf.content_type not in ("application/pdf", "application/x-pdf"):
        return JsonResponse({"error": "Chỉ được tải file PDF!"}, status=400)
    
    MAX_MB = settings.MAX_MB
    if getattr(pdf, "size", 0) > MAX_MB * 1024 * 1024:
        return JsonResponse({"error": f"File vượt quá {MAX_MB} MB!"}, status=400)
    
    name_software, version_software = util.extract_software_name(pdf.name)
    if not name_software or not version_software:
        return JsonResponse({"error": "File không hợp lệ!"}, status=400)
    
    
    # 3) Paths
    docs_dir = os.path.join(settings.BASE_DIR,'docs')
    images_dir = os.path.join(settings.BASE_DIR, 'extracted_images')
    
    # 4) Xóa cũ (nếu có) + cập nhật chỉ mục
    try:
        util.remove_old_software_pdf(docs_dir, pdf.name, name_software, version_software)
    except Exception:
        return JsonResponse({"error": f"Lỗi khi xóa file cũ!"}, status=500)
    
    # 5) Lưu file mới
    try:
        saved_absolute_path = util.save_pdf_to_storage(pdf, docs_dir)
    except Exception:
        return JsonResponse({"error": f"Lỗi khi lưu file!"}, status=500)
    
    # 6) Ingest
    try:
        ingest_pdf.ingest_pdf_docling(saved_absolute_path, name_software, version_software, images_dir)
    except Exception:
        return JsonResponse({"error": f"Không thể upload file!"}, status=500)

    return JsonResponse({'message': 'Upload file thành công!'})
        


@csrf_exempt
def chat(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Yêu cầu là phương thức POST!"}, status=405)
    
    data = json.loads(request.body)
    question = data.get('question', "")
    source = data.get('source',"")
    model = data.get('model', "")
    
    # Optional hybrid retrieval parameters
    use_hybrid = data.get('use_hybrid', False)  # Default to False for backward compatibility
    hybrid_weights = data.get('hybrid_weights', [0.7, 0.3])  # Dense, Sparse weights
    
    parts = source.split("_")
    if len(parts) > 2:
        name_software = parts[1]
    else:
        name_software = None
            
    start_time = time.time()
    answer = rag_engine.query_with_rag_use_qdrant(
        question, name_software, model, 
        use_hybrid=use_hybrid, 
        hybrid_weights=hybrid_weights
    )
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

@csrf_exempt
def login (request):
    if request.method != "POST":
        return JsonResponse({"error" : "Yêu cầu là phương thức POST!"}, status=405)
    
    data = json.loads(request.body)
    username = data.get('username', '')
    password = data.get('password', '')
    
    if not username or not password:
        return JsonResponse({"error" : "Tài khoản và mật khẩu không được trống!"}, status=400)
    
    # Kiểm tra thông tin đăng nhập hợp lệ không
    valid_user = database_util.get_user_by_account(username)
    if not valid_user or not password_encr.check_password(password.encode('utf-8'), valid_user['user_password'].encode('utf-8')):
        return JsonResponse({"error" : "Thông tin tài khoản hoặc mật khẩu không chính xác!"}, status=401)
    
    # Tạo jwt token
    try: 
        token = jwt_token_util.create_jwt_token(valid_user)
    except Exception:
        return JsonResponse({"error" : "Lỗi hệ thống!"}, status=500)
    
    response = JsonResponse({"message" : "Đăng nhập thành công"})
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        secure=settings.SECURE_COOKIE,
        samesite="Strict",
        max_age=int(settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
    )
    return response

@csrf_exempt
def logout (request):
    if request.method != "POST":
        return JsonResponse({"error" : "Yêu cầu là phương thức POST!"}, status=405)
    
    resp = JsonResponse({"message": "Đăng xuất thành công!"})
    resp.delete_cookie("access_token")
        
    

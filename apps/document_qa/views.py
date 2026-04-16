import os
import uuid
from datetime import datetime, timezone
import threading
import hashlib

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt


from .models import Document

# Import các service
from apps.document_qa.service import AIService, DocumentService

# Khởi tạo service một lần duy nhất
ai_service = AIService()
doc_service = DocumentService()

def _build_response(
    *,
    status,
    session_id,
    request_id,
    message,
    answer=None,
    user_query=None,
    error_code=None,
    http_status=200,
    extra=None
):
    """Hàm bổ trợ để format dữ liệu JSON trả về đồng nhất"""
    payload = {
        "status": status,
        "message": message,
        "answer": answer,
        "session_id": session_id,
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "model": getattr(ai_service, "model_name", "gemini-1.5-flash"),
            "history_limit": getattr(ai_service, "history_limit", 10),
        },
        "input": {
            "user_query": user_query
        },
        "error": {
            "code": error_code
        } if status == "error" else None
    }

    if extra:
        payload["meta"].update(extra)

    return JsonResponse(payload, status=http_status)

@csrf_exempt
def chat_view(request):
    """Xử lý giao diện và logic nhắn tin AI"""
    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key
    request_id = str(uuid.uuid4())

    if request.method != "POST":
        return render(request, "chat.html")

    message = request.POST.get("message", "").strip()
    if not message:
        return _build_response(
            status="error",
            session_id=session_id,
            request_id=request_id,
            message="Thiếu nội dung câu hỏi.",
            user_query=message,
            error_code="EMPTY_MESSAGE",
            http_status=400
        )

    try:
        # Gọi AIService để lấy câu trả lời
        response_data = ai_service.get_chat_response(session_id, message)
        
        # Xử lý nếu kết quả trả về là tuple (answer, history)
        answer = response_data[0] if isinstance(response_data, tuple) else response_data

        return _build_response(
            status="success",
            session_id=session_id,
            request_id=request_id,
            message="Xử lý thành công.",
            answer=answer,
            user_query=message,
            http_status=200
        )

    except Exception as err:
        err_text = str(err)
        err_upper = err_text.upper()

        # Phân loại lỗi API
        if "RESOURCE_EXHAUSTED" in err_upper or "429" in err_upper:
            code = "QUOTA_EXCEEDED"
            user_msg = "Hệ thống AI đang vượt quá hạn mức (quota), vui lòng thử lại sau."
            status_code = 429
        elif "NOT_FOUND" in err_upper or "404" in err_upper:
            code = "MODEL_NOT_FOUND"
            user_msg = "Model AI không tồn tại hoặc không hỗ trợ."
            status_code = 502
        elif "API_KEY" in err_upper or "PERMISSION_DENIED" in err_upper:
            code = "AUTH_ERROR"
            user_msg = "Lỗi xác thực API Key."
            status_code = 401
        else:
            code = "AI_SERVICE_ERROR"
            user_msg = "Không thể kết nối tới dịch vụ AI."
            status_code = 502

        extra_meta = {}
        if settings.DEBUG:
            extra_meta["debug_error"] = err_text

        return _build_response(
            status="error",
            session_id=session_id,
            request_id=request_id,
            message=user_msg,
            user_query=message,
            error_code=code,
            http_status=status_code,
            extra=extra_meta
        )

@csrf_exempt
def file_manager_view(request):
    """Hiển thị trang quản lý file"""
    return render(request, "file_manager.html")

def background_embedding(full_file_path, unique_name, doc_id):
    """Hàm này sẽ chạy ở luồng riêng biệt"""
    try:
        print(f"--- Tiến thành Embedding cho: {unique_name} ---")
        # Thực hiện embedding (bước tốn thời gian)
        num_chunks = doc_service.process_file(full_file_path, unique_name)
        
        # Sau khi xong, cập nhật trạng thái trong SQL
        doc_record = Document.objects.get(id=doc_id)
        doc_record.status = "Success"
        # Bạn có thể lưu thêm số lượng chunks nếu muốn
        doc_record.save()
        print(f"--- Embedding hoàn tất cho: {unique_name} ({num_chunks} chunks) ---")
    except Exception as e:
        doc_record = Document.objects.get(id=doc_id)
        doc_record.status = "Error"
        doc_record.save()
        print(f"--- Lỗi embedding {unique_name}: {str(e)} ---")

def calculate_file_hash(file_obj):
    """Tính mã băm để nhận diện nội dung file duy nhất"""
    sha256_hash = hashlib.sha256()
    # Đọc theo từng chunk để không bị tràn RAM với file lớn
    for chunk in file_obj.chunks():
        sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

@csrf_exempt
def upload_document(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']


        file_hash = calculate_file_hash(file)
        if Document.objects.filter(file_hash=file_hash).exists():
            return JsonResponse({'status': 'error', 'message': 'Nội dung file này đã tồn tại trong hệ thống.'})
        
        # 1. Xử lý tên và lưu file vật lý (Bước này nhanh, làm trực tiếp)
        unique_name = doc_service.get_unique_filename(file.name)
        file_path_in_storage = os.path.join('uploads', unique_name)
        saved_path = default_storage.save(file_path_in_storage, file)
        full_file_path = default_storage.path(saved_path)

        # 2. Tạo bản ghi SQL với trạng thái 'Processing'
        doc_record = Document.objects.create(
            file_name=file.name,
            unique_name=unique_name,
            file_path=full_file_path,
            file_hash=file_hash,
            status="Processing"
        )

        # 3. KÍCH HOẠT CHẠY NỀN: Đẩy việc Embedding sang một Thread khác
        thread = threading.Thread(
            target=background_embedding, 
            args=(full_file_path, unique_name, doc_record.id)
        )
        thread.start()

        # 4. TRẢ VỀ NGAY LẬP TỨC
        return JsonResponse({
            'status': 'success', 
            'message': f'File "{file.name}" đang được xử lý nền. Bạn có thể theo dõi trạng thái ở bảng quản lý.'
        })
                
    return JsonResponse({'status': 'error', 'message': 'Yêu cầu không hợp lệ.'})

@csrf_exempt
def get_files_api(request):
    """API trả về danh sách file dạng JSON để AJAX gọi"""
    page_number = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 5)
    
    files_queryset = Document.objects.all().order_by('-upload_at')
    paginator = Paginator(files_queryset, page_size)
    page_obj = paginator.get_page(page_number)
    
    data = []
    for f in page_obj:
        data.append({
            "id": f.id,
            "file_name": f.file_name,
            "status": f.status,
            "upload_at": f.upload_at.strftime("%Y-%m-%d %H:%M")
        })
        
    return JsonResponse({
        "files": data,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "number": page_obj.number,
        "num_pages": paginator.num_pages
    })

@csrf_exempt
def delete_document(request, file_id):
    """Xóa đồng bộ: SQL -> Vector DB -> Physical File"""
    if request.method == "POST":
        try:
            # 1. Tìm tài liệu trong SQL bằng UUID
            doc = Document.objects.get(id=file_id)
            
            # 2. Gọi service để xóa Vector trong FAISS và File trên ổ đĩa
            # Sử dụng unique_name làm chìa khóa định danh
            success = doc_service.delete_document_vector(doc.unique_name)
            
            # 3. Xóa bản ghi trong SQL
            doc.delete()
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Đã xóa tài liệu {doc.file_name} thành công.'
            })
        except Document.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy tài liệu.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Phương thức không được hỗ trợ.'}, status=405)
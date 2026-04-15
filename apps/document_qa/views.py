import os
import uuid
from datetime import datetime, timezone

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import default_storage

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


def file_manager_view(request):
    """Hiển thị trang quản lý file"""
    return render(request, "file_manager.html")


def upload_document(request):
    """Xử lý upload tài liệu và nạp vào VectorDB (RAG)"""
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        
        # 1. Lưu file tạm thời vào media/uploads/
        file_name = default_storage.save('uploads/' + file.name, file)
        file_path = default_storage.path(file_name)

        try:
            # 2. Gọi DocumentService để xử lý tài liệu (Cắt nhỏ + Embedding)
            num_chunks = doc_service.process_file(file_path)
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Thành công! Đã nạp {num_chunks} đoạn kiến thức từ file {file.name}.'
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
        # finally:
        #     # Nếu muốn xóa file sau khi đã nạp vào DB thì bỏ comment dòng dưới
        #     if os.path.exists(file_path):
        #         os.remove(file_path)
                
    return JsonResponse({'status': 'error', 'message': 'Yêu cầu không hợp lệ hoặc thiếu file.'})
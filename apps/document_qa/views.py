import os
from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt
from apps.document_qa.service import AIService # Import từ folder service
from apps.document_qa.service import DocumentService

# Khởi tạo một lần duy nhất
ai_service = AIService()
doc_service = DocumentService()

@csrf_exempt
def chat_view(request):
    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key

    if request.method == "POST":
        message = request.POST.get('message')
        # Giả sử bạn lấy user.id từ request.user (nếu đã login)
        response_text = ai_service.get_chat_response(session_id, message)
        
        return JsonResponse({
            'status': 'success',
            'answer': response_text,
            'session_id': session_id
        })
    return render(request, 'chat.html')

@csrf_exempt
def file_manager_view(request):
    return render(request, 'file_manager.html')


@csrf_exempt
def upload_document(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        
        # 1. Lưu file tạm thời vào media/uploads/
        file_name = default_storage.save('uploads/' + file.name, file)
        file_path = default_storage.path(file_name)

        try:
            # 2. Gọi DocumentService để băm nhỏ và Embed vào FAISS
            num_chunks = doc_service.process_file(file_path)
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Thành công! Đã nạp {num_chunks} đoạn kiến thức từ file {file.name}.'
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
        # finally:
        #     # 3. Sau khi Embed xong thì xóa file thô đi để tiết kiệm bộ nhớ server
        #     if os.path.exists(file_path):
        #         os.remove(file_path)
                
    return JsonResponse({'status': 'error', 'message': 'Yêu cầu không hợp lệ.'})
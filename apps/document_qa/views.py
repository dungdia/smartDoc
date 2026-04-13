from django.shortcuts import render
from django.http import JsonResponse
from apps.document_qa.service import AIService # Import từ folder service

# Khởi tạo một lần duy nhất
ai_service = AIService()

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

def file_manager_view(request):
    return render(request, 'file_manager.html')
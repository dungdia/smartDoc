from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),  # Khi gõ trang chủ, vào chat
    path('files/', views.file_manager_view, name='file_manager'), # Quản lý file
    path('upload/', views.upload_document, name='upload_document'), # API upload file
    path('get_files_api/', views.get_files_api, name='get_files_api'), # API lấy danh sách file
    path('delete-file/<uuid:file_id>/', views.delete_document, name='delete_document'), # API xóa file
]
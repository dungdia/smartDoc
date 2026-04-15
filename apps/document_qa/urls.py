from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),  # Khi gõ trang chủ, vào chat
    path('files/', views.file_manager_view, name='file_manager'), # Quản lý file
    path('upload/', views.upload_document, name='upload_document'), # API upload file
]
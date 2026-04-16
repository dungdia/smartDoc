from django.db import models

# Create your models here.
from django.db import models
import uuid

class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    unique_name = models.CharField(max_length=255, unique=True, null=True)
    # Lưu checksum (hash) để tránh xử lý lại cùng một nội dung file
    file_hash = models.CharField(max_length=64, unique=True, null=True) 
    status = models.CharField(max_length=50, default="Pending")
    upload_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name

class KnowledgeChunk(models.Model):
    """Lưu vết các đoạn văn bản để đồng bộ với Vector/Graph DB"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField()
    vector_id = models.CharField(max_length=100) # ID trong FAISS/Milvus
    content_summary = models.TextField(blank=True) # Tóm tắt ngắn để GraphRAG dễ tạo node
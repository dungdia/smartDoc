import os
import magic
import shutil
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

class DocumentService:
    def __init__(self):
        # Sử dụng model local để tạo vector

        self.embeddings = HuggingFaceEmbeddings(model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
        self.vector_db_path = "vector_db/faiss_index"
        self.upload_dir = "media/uploads"
        
        # Đảm bảo thư mục lưu trữ tồn tại
        os.makedirs(self.upload_dir, exist_ok=True)

    def get_unique_filename(self, filename):
        """Xử lý trùng tên file: 'document.pdf' -> 'document_1.pdf'"""
        base_path = Path(self.upload_dir) / filename
        if not base_path.exists():
            return filename
        
        name = base_path.stem
        suffix = base_path.suffix
        counter = 1
        while (Path(self.upload_dir) / f"{name}_{counter}{suffix}").exists():
            counter += 1
        return f"{name}_{counter}{suffix}"

    def process_file(self, file_path, unique_name):
        """Đọc file, chia nhỏ và gắn metadata định danh duy nhất"""
        mime = magic.from_file(file_path, mime=True)
        
        if mime == 'application/pdf':
            loader = PyPDFLoader(file_path)
        elif mime == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError(f"Định dạng {mime} không được hỗ trợ.")

        # Load nội dung
        pages = loader.load()
        
        # Chia nhỏ văn bản (Chunking)
        # Giữ chunk_size vừa phải để GraphRAG dễ trích xuất thực thể sau này
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        docs = text_splitter.split_documents(pages)

        # Gắn metadata 'source' là unique_name. 
        # Đây là chìa khóa để xóa đúng file và tạo quan hệ trong Graph DB sau này.
        for doc in docs:
            doc.metadata["source"] = unique_name 

        # Lưu vào FAISS
        if os.path.exists(self.vector_db_path):
            vector_db = FAISS.load_local(
                self.vector_db_path, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
            vector_db.add_documents(docs)
        else:
            vector_db = FAISS.from_documents(docs, self.embeddings)
        
        vector_db.save_local(self.vector_db_path)
        return len(docs)

    def delete_document_vector(self, unique_name):
        """Chỉ xóa các vector thuộc về file unique_name, không ảnh hưởng file khác"""
        if not os.path.exists(self.vector_db_path):
            return False

        # 1. Tải toàn bộ chỉ mục hiện tại
        vector_db = FAISS.load_local(
            self.vector_db_path, 
            self.embeddings, 
            allow_dangerous_deserialization=True
        )

        # 2. Lọc các ID trong docstore có metadata 'source' trùng với file cần xóa
        # docstore._dict lưu trữ tất cả các mảnh (chunks) đã index
        ids_to_remove = [
            id for id, doc in vector_db.docstore._dict.items() 
            if doc.metadata.get('source') == unique_name
        ]

        if ids_to_remove:
            # 3. Chỉ xóa các ID của file đó
            vector_db.delete(ids_to_remove)
            
            # 4. Ghi đè lại index đã được làm sạch lên ổ đĩa
            vector_db.save_local(self.vector_db_path)
            
            # 5. Xóa file vật lý trong thư mục media
            physical_path = os.path.join(self.upload_dir, unique_name)
            if os.path.exists(physical_path):
                os.remove(physical_path)
            return True
            
        return False
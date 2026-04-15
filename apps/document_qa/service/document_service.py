import os
import magic
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

class DocumentService:
    def __init__(self):
        # Model này sẽ chạy local trên máy bạn (WSL), không tốn tiền API
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_db_path = "vector_db/faiss_index"

    def process_file(self, file_path):
        # Kiểm tra MIME type như bạn yêu cầu
        mime = magic.from_file(file_path, mime=True)
        
        if mime == 'application/pdf':
            loader = PyPDFLoader(file_path)
        elif mime == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError(f"Hệ thống không hỗ trợ định dạng: {mime}")

        # Đọc và chia nhỏ
        pages = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        docs = text_splitter.split_documents(pages)

        # Lưu vào FAISS
        if os.path.exists(self.vector_db_path):
            vector_db = FAISS.load_local(self.vector_db_path, self.embeddings, allow_dangerous_deserialization=True)
            vector_db.add_documents(docs)
        else:
            vector_db = FAISS.from_documents(docs, self.embeddings)
        
        vector_db.save_local(self.vector_db_path)
        return len(docs)
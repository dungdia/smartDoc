# 🤖 SmartDoc AI - Hybrid RAG & GraphRAG System

SmartDoc AI là hệ thống phân tích tài liệu thông minh. Hệ thống kết hợp giữa **Vector Search (FAISS)** để tìm kiếm ngữ nghĩa và **Knowledge Graph (Neo4j)** để phân tích các mối quan hệ phức tạp giữa các thực thể trong tài liệu.

## 🛠 Yêu cầu hệ thống (Prerequisites)

Dự án chạy trên **WSL2 (Ubuntu)**. Cần cài đặt các thành phần sau:

### 1. Cài đặt Neo4j & Libmagic
```bash
# Cài đặt Neo4j
wget -O - [https://debian.neo4j.com/neotechnology.gpg.key](https://debian.neo4j.com/neotechnology.gpg.key) | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] [https://debian.neo4j.com](https://debian.neo4j.com) stable 5" | sudo tee -a /etc/apt/sources.list.d/neo4j.list
sudo apt update && sudo apt install neo4j -y

# Cài đặt thư viện xử lý định dạng file (MIME type)
sudo apt install libmagic1 -y
```

---

## 🚀 Hướng dẫn cài đặt dự án (Setup)

### 1. Khởi tạo môi trường ảo & Cài đặt thư viện
```bash
python3 -m venv venv
source venv/bin/activate
make install  # Sử dụng Makefile để cài đặt toàn bộ requirements
```

### 2. Cấu hình biến môi trường
Tạo file `.env` tại thư mục gốc:
```env
DEBUG=True
SECRET_KEY=your-django-key
GOOGLE_API_KEY=your-gemini-key

# Neo4j Config (Mặc định sau khi bạn đã đổi pass tại localhost:7474)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_new_password

# AI Config
CHAT_HISTORY_LIMIT=10
LLM_MODEL=gemini-1.5-flash
```

### 3. Khởi tạo Database & Thư mục
```bash
make migrate
mkdir -p vector_db media/uploads
```

---

## ⚡ Các tính năng nổi bật

* **Đa định dạng**: Hỗ trợ PDF và DOCX.
* **MIME Type Validation**: Kiểm tra nội dung file thực tế bằng `python-magic` để đảm bảo bảo mật.
* **Hybrid Retrieval**: 
    * **Vector RAG**: Tìm kiếm đoạn văn bản tương đồng qua FAISS index.
    * **Graph RAG**: Truy vấn các mối quan hệ thực thể qua Neo4j Graph.
* **Session-based Chat**: Tự động tạo session mới khi người dùng truy cập lại, lưu trữ lịch sử chat tạm thời trong RAM.

---

## 🏃 Thao tác nhanh với Makefile

| Lệnh | Mô tả |
| :--- | :--- |
| `make run` | Khởi chạy Django Server (127.0.0.1:8000) |
| `make neo4j-start` | Bật service Neo4j |
| `make migrate` | Cập nhật Database (Models) |
| `make clean` | Dọn dẹp cache và file rác python |

---

## 📁 Cấu trúc thư mục Service
Dự án áp dụng mô hình Service Layer để tách biệt logic AI:
- `services/ai_service.py`: Điều phối luồng chat và quản lý session.
- `services/document_service.py`: Xử lý nạp file, băm nhỏ (chunking) và định danh MIME type.
- `services/graph_rag_service.py`: Xử lý trích xuất và truy vấn trên Neo4j.
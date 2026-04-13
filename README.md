# 🤖 SmartDoc AI - RAG & GraphRAG System

SmartDoc AI là hệ thống phân tích tài liệu thông minh sử dụng kiến trúc RAG (Retrieval-Augmented Generation). Dự án kết hợp giữa Vector Search (FAISS) và Knowledge Graph (Neo4j) để tối ưu hóa khả năng trả lời câu hỏi từ file PDF/Docx.

## 🛠 Yêu cầu hệ thống (Prerequisites)

Dự án được phát triển trên môi trường **WSL2 (Ubuntu)**. Đảm bảo bạn đã cài đặt:
* **Python**
* **Neo4j Community Edition** (Dành cho GraphRAG)
* **Make** (Công cụ quản lý lệnh nhanh)

### 1. Cài đặt Neo4j trên WSL (Chưa có)
```bash
# Thêm repository và cài đặt Neo4j
wget -O - [https://debian.neo4j.com/neotechnology.gpg.key](https://debian.neo4j.com/neotechnology.gpg.key) | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] [https://debian.neo4j.com](https://debian.neo4j.com) stable 5" | sudo tee -a /etc/apt/sources.list.d/neo4j.list
sudo apt update && sudo apt install neo4j -y

# Khởi động service
sudo service neo4j start
```
*Lưu ý: Sau khi cài đặt, truy cập `http://localhost:7474` để đổi mật khẩu mặc định (user: `neo4j`, pass: `neo4j`).*

---

## 🚀 Hướng dẫn cài đặt dự án (Setup)

### 1. Khởi tạo môi trường ảo
```bash
# Tạo và kích hoạt venv
python3 -m venv venv
source venv/bin/activate
```

### 2. Cài đặt thư viện
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Tạo file `.env` tại thư mục gốc dự án:
```env
SECRET_KEY=django-secert-key-placeholder
GEMINI_API_KEY=your_api_key_here
DEBUG=True
CHAT_HISTORY_LIMIT=10
LLM_MODEL=gemini-2.5-flash
```

### 4. Khởi tạo Database
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 🏃 Thao tác nhanh với Makefile

Dự án tích hợp `Makefile` để đơn giản hóa các câu lệnh trên WSL:

| Lệnh | Mô tả |
| :--- | :--- |
| `make run` | Khởi chạy Django Server (http://127.0.0.1:8000) |
| `make neo4j-start` | Bật service Neo4j (cần nhập mật khẩu sudo) |
| `make neo4j-stop` | Tắt service Neo4j |
| `make migrate` | Đồng bộ cấu trúc Database |
| `make install` | Cài đặt/Cập nhật thư viện từ requirements.txt |
| `make clean` | Xóa các file rác python (__pycache__) |

---

## 📁 Cấu trúc thư mục dự án
```text
smartdoc_project/
├── apps/
│   └── document_qa/        # App chính xử lý tài liệu & Chat
│       ├── services/       # Bộ não AI (VectorRAG, GraphRAG)
│       ├── templates/      # Giao diện Chat & Quản lý file
│       └── models.py       # Lưu trữ lịch sử chat & metadata tài liệu
├── core/                   # Cấu hình dự án Django
├── manage.py
├── Makefile                # Shortcut commands
└── requirements.txt        # Danh sách thư viện
```

## 📝 Lưu ý phát triển
* **Markdown Rendering**: Giao diện hỗ trợ hiển thị Markdown. Đảm bảo đã tích hợp `marked.js` trong template để tin nhắn AI hiển thị xuống dòng và bôi đậm chuẩn.
* **Session Management**: Hệ thống tự động tạo Session ID mới khi người dùng truy cập để tách biệt lịch sử hội thoại.
```
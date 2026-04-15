import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


# Lưu trữ nhiều session trong RAM: { 'session_id_1': history1, 'session_id_2': history2 }
sessions_db = {}

class AIService:
    def __init__(self):
        self.model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        self.history_limit = int(os.getenv("CHAT_HISTORY_LIMIT", 10))
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )

        self.system_instruction = SystemMessage(content=(
            "Bạn là trợ lý AI chuyên gia của hệ thống SmartDoc AI. "
            "Nhiệm vụ của bạn là hỗ trợ người dùng phân tích tài liệu, trả lời câu hỏi và tóm tắt thông tin. "
            "1. Phân tích nội dung: Khi có dữ liệu từ tài liệu (PDF/Docx), hãy ưu tiên trả lời dựa trên nội dung đó. "
            "2. Phong cách: Trả lời ngắn gọn, rõ ràng, tập trung vào ý chính. "
            "3. Ngôn ngữ: Phản hồi bằng ngôn ngữ người dùng sử dụng (mặc định là tiếng Việt). "
            "4. Giới hạn: Nếu thông tin không có trong tài liệu và bạn không chắc chắn, hãy thành thật thông báo cho người dùng."
        ))

    def get_chat_response(self, session_id, user_query):
        # 1. Kiểm tra xem session_id này đã có lịch sử chưa, nếu chưa thì tạo mới
        if session_id not in sessions_db:
            sessions_db[session_id] = ChatMessageHistory()
        
        history = sessions_db[session_id]
        
        # 2. Lấy context n tin gần nhất từ session này
        all_messages = history.messages
        limited_history = all_messages[-(self.history_limit * 2):] if all_messages else []

        context = ""
        vector_db_path = "vector_db/faiss_index"
        if os.path.exists(vector_db_path) and os.path.exists(os.path.join(vector_db_path, "index.faiss")):
            # Nạp database lên (với embeddings bạn đã khởi tạo trong __init__)
            vector_db = FAISS.load_local(
                "vector_db/faiss_index", 
                self.embeddings, 
                allow_dangerous_deserialization=True
        )
            # Lấy ra 3 đoạn văn bản giống câu hỏi nhất
            docs = vector_db.similarity_search(user_query, k=3)
            context = "\n".join([d.page_content for d in docs])
        rag_content = f"Tài liệu cung cấp:\n{context}\n\nCâu hỏi: {user_query}"

        # 3. Gọi AI với context của riêng session đó
        current_messages = [self.system_instruction] + limited_history + [HumanMessage(content=rag_content)]
        response = self.llm.invoke(current_messages)
        ai_answer = response.content

        # 4. Lưu lại vào đúng session
        history.add_user_message(user_query)
        history.add_ai_message(ai_answer)

        return ai_answer
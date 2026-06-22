# RAG Chatbot Project

## Giới thiệu (Introduction)
RAG Chatbot là một ứng dụng web được xây dựng dựa trên framework Django, ứng dụng công nghệ Retrieval-Augmented Generation (RAG) và các mô hình ngôn ngữ lớn (LLMs). Hệ thống cho phép người dùng tải lên các tài liệu, trích xuất thông tin và trò chuyện trực tiếp với tài liệu đó một cách thông minh thông qua giao diện chat. Dự án sử dụng LangChain, Docling để xử lý tài liệu và các Vector Database (như Redis, Qdrant) để lưu trữ ngữ nghĩa.

## Các chức năng nổi bật (Key Features)
- **Tải lên và xử lý tài liệu**: Hỗ trợ tải lên file PDF và trích xuất nội dung sử dụng thư viện `docling`.
- **Trò chuyện với tài liệu (RAG)**: Đặt câu hỏi và nhận câu trả lời chính xác dựa trên ngữ cảnh của tài liệu đã tải lên.
- **So sánh mô hình (Model Comparison)**: Cho phép so sánh kết quả trả lời giữa các mô hình ngôn ngữ khác nhau (ví dụ: các model từ OpenAI, Groq, HuggingFace).
- **Quản lý Prompt**: Người dùng có thể tùy chỉnh, thêm mới hoặc cập nhật các prompt để điều chỉnh cách bot trả lời.
- **Hệ thống phản hồi (Feedback)**: Cho phép người dùng đánh giá và gửi phản hồi về chất lượng câu trả lời của chatbot.
- **Xác thực người dùng**: Tích hợp tính năng đăng nhập và quản lý thông qua API.

## Các API chính (Main APIs)
Các endpoint chính được định nghĩa trong hệ thống (`chat/urls.py`):
- `GET /` (`chat_view`): Giao diện chính của ứng dụng chat.
- `POST /api/upload/`: API tải lên file tài liệu (PDF) và xử lý vector hóa.
- `POST /api/chat/`: API gửi tin nhắn và nhận phản hồi từ chatbot dựa trên tài liệu.
- `POST /api/chat/compare/`: API so sánh kết quả phản hồi từ nhiều LLM khác nhau cho cùng một câu hỏi.
- `POST /api/feedback/`: API ghi nhận đánh giá (feedback) của người dùng về câu trả lời.
- `POST /api/login/`: API đăng nhập xác thực người dùng.
- `GET /api/loginPage/`: Trả về giao diện trang đăng nhập.
- `GET /api/promptPage/`: Trả về giao diện trang quản lý prompt.
- `POST /api/addprompt/`: API thêm mới hoặc cập nhật prompt tùy chỉnh.

## Cách tải và cài đặt (Installation & Setup)

### Cài đặt chạy trực tiếp (Local Setup)
1. **Clone repository** và di chuyển vào thư mục `RAGchatbot`.
2. **Cài đặt các thư viện cần thiết**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Chạy Redis thông qua Docker** (port mặc định 6379) - Bắt buộc để làm Vector DB:
   - Chạy lần đầu:
     ```bash
     docker run -d --name redis -p 6379:6379 redis:latest
     ```
   - Chạy các lần sau:
     ```bash
     docker start redis
     ```
   *(Sử dụng lệnh `docker ps -a` để kiểm tra danh sách container)*
4. **Cấu hình môi trường**: Tạo file `.env` chứa các API keys cần thiết (ví dụ: `OPENAI_API_KEY`, `GROQ_API_KEY`,...).
5. **Cấu hình xử lý tài liệu**: Tắt tính năng CUDA accelerator trong quá trình trích xuất bằng Docling nếu máy tính không có GPU.
6. **Khởi chạy Server Django**:
   ```bash
   python manage.py runserver
   ```
   Ứng dụng sẽ chạy tại địa chỉ: `http://127.0.0.1:8000/`

### Cài đặt thông qua Docker
Dự án có cung cấp sẵn `Dockerfile` để build và chạy thông qua Docker:
1. Build image:
   ```bash
   docker build -t ragchatbot .
   ```
2. Chạy container:
   ```bash
   docker run -p 7860:7860 --env-file .env ragchatbot
   ```

## Các tính năng tiềm năng (Potential Features)
Những cải tiến đang được cân nhắc cho các phiên bản tương lai:
1. Lưu trữ bộ nhớ hội thoại (Conversation memory).
2. Chức năng Đăng xuất (Logout).
3. Cho phép chọn loại tài liệu trước khi tải lên.
4. Bắt buộc người dùng chọn tài liệu trước khi bắt đầu chat.
5. Ghi log chi tiết hệ thống (Detailed logging).

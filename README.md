# Multimodal Real Estate AI Agent

Chào bạn! Đây là một dự án demo thú vị kết hợp trí tuệ nhân tạo với lĩnh vực bất động sản. Ứng dụng này giúp người dùng:

- đặt câu hỏi về bất động sản một cách tự nhiên
- nhận được gợi ý định giá gần đúng bằng mô hình học máy
- tra cứu thông tin nội bộ và quy hoạch thông qua AI
- xem kết quả trên một giao diện thân thiện và dễ sử dụng

---

## Dự án này làm gì?

Hệ thống có thể hiểu được câu hỏi của người dùng, xử lý thông tin về địa chỉ, diện tích, số tầng, nội thất và từ đó tạo ra một báo cáo định giá gần đúng. Ngoài ra, nếu người dùng hỏi về tài liệu nội bộ, hệ thống cũng có thể tìm kiếm thông tin liên quan bằng công nghệ RAG.

Nói ngắn gọn, đây là một “trợ lý AI cho bất động sản” – vừa có thể tư vấn, vừa có thể hỗ trợ phân tích dữ liệu.

---

## Tính năng nổi bật

### 1. Trò chuyện với AI Agent
Bạn có thể nhập câu hỏi bằng tiếng Việt và hệ thống sẽ tự động hiểu bạn đang hỏi về:
- bất động sản
- định giá
- quy hoạch
- tài liệu nội bộ doanh nghiệp

### 2. Dự đoán giá bất động sản
Dự án sử dụng mô hình XGBoost để xây dựng và vận hành hệ thống định giá bất động sản. Cụ thể:
- XGBoost được dùng để huấn luyện mô hình từ dữ liệu lưu trong database
- Sau khi huấn luyện, mô hình được lưu lại và dùng để dự báo giá nhà mới
- Khi người dùng đặt câu hỏi hoặc khi LLM tạo ra prompt liên quan đến thông tin bất động sản, dữ liệu đầu vào sẽ được chuyển sang dạng feature số và đưa vào XGBoost để lấy kết quả dự đoán

Các yếu tố đầu vào cho XGBoost bao gồm:
- tọa độ địa lý
- diện tích đất
- số tầng
- điểm nội thất
- chiều rộng hẻm
- giá trị không gian lân cận được tính từ dữ liệu lịch sử

### 3. Tra cứu thông tin bằng RAG
Nếu câu hỏi liên quan đến tài liệu nội bộ, hệ thống sẽ tìm kiếm context phù hợp từ vector database và đưa vào prompt cho LLM.

### 4. Hỗ trợ dữ liệu hình ảnh và video
Nếu bạn đính kèm ảnh hoặc video, hệ thống có thể xử lý dữ liệu đa phương thức để hỗ trợ phân tích tốt hơn.

---

## Công nghệ được sử dụng

### Phía backend
- Python
- FastAPI
- Ollama + LangChain
- XGBoost
- scikit-learn
- pandas / numpy
- MySQL
- ChromaDB
- geopy

### Phía frontend
- Vue 3
- Vite
- Element Plus
- Axios

### Công cụ vận hành
- Docker
- Docker Compose

---

## Cách chạy dự án

### Yêu cầu
- Máy đã cài Docker và Docker Compose
- Kết nối internet ban đầu để pull image

### Chạy toàn bộ hệ thống
```bash
docker compose up --build
```

### Các địa chỉ sau khi chạy
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Ollama: http://localhost:11434
- Chroma UI: http://localhost:8090

---

## Cấu trúc dự án

```text
backend/          # API và logic AI
frontend/         # giao diện người dùng
data_source/      # dữ liệu đầu vào
sales_uploads/    # dữ liệu bán hàng / tài liệu upload
models_storage/   # file mô hình XGBoost và scaler
vector_db/        # dữ liệu vector cho RAG
```

---

## Quy trình hoạt động

1. Người dùng gửi câu hỏi hoặc đính kèm ảnh/video
2. Backend phân loại câu hỏi và trích xuất thông tin quan trọng
3. Dữ liệu bất động sản được lấy từ database và chuẩn bị thành các feature số
4. XGBoost được dùng để huấn luyện mô hình từ dữ liệu này và lưu lại thành file model AI
5. Khi cần dự đoán giá cho một giao dịch mới, dữ liệu đầu vào được chuyển thành feature và đưa vào XGBoost để sinh ra kết quả dự đoán
6. Nếu cần, hệ thống tra cứu tài liệu nội bộ bằng RAG
7. LLM tổng hợp lại thành một câu trả lời hoặc báo cáo dễ hiểu

---

## Quy trình training tạo ra file XGBoost

Dưới đây là quy trình training model định giá bất động sản trong dự án, được thực hiện bằng Python và XGBoost.

### Bước 1: Kết nối dữ liệu từ database
- Công nghệ dùng: Python, SQLAlchemy, pandas
- Mục đích: lấy dữ liệu bất động sản từ MySQL
- File liên quan: [backend/ai_training_engine/data_loader.py](backend/ai_training_engine/data_loader.py)
- Dữ liệu lấy về thường gồm các trường như:
  - địa chỉ
  - tọa độ latitude/longitude
  - diện tích đất
  - số tầng
  - điểm nội thất
  - chiều rộng hẻm
  - giá thực tế

### Bước 2: Chuẩn bị dữ liệu và trích xuất feature
- Công nghệ dùng: pandas, numpy, scikit-learn
- Mục đích: biến dữ liệu thô thành các feature phù hợp để học máy sử dụng
- File liên quan: [backend/ai_training_engine/preprocessor.py](backend/ai_training_engine/preprocessor.py)
- Các bước trong phần này:
  - tính toán giá trên mỗi m2
  - tạo feature không gian bằng KNN để lấy giá trung bình lân cận
  - chuẩn hóa dữ liệu bằng StandardScaler

### Bước 3: Chia dữ liệu thành tập train và test
- Công nghệ dùng: scikit-learn
- Mục đích: kiểm tra hiệu quả mô hình bằng cách đánh giá trên dữ liệu chưa từng thấy
- Hàm dùng: train_test_split
- Ý nghĩa: dữ liệu được chia để huấn luyện và đánh giá mô hình một cách khách quan

### Bước 4: Huấn luyện mô hình bằng XGBoost
- Công nghệ dùng: XGBoost
- Mục đích: học mối quan hệ giữa các feature đầu vào và giá bất động sản mục tiêu
- File liên quan: [backend/ai_training_engine/xgboost_trainer.py](backend/ai_training_engine/xgboost_trainer.py)
- Mô hình dùng: XGBRegressor
- Quá trình này bao gồm:
  - khởi tạo mô hình regression
  - fit dữ liệu train
  - dùng tập test để đánh giá sai số

### Bước 5: Lưu model ra file
- Công nghệ dùng: XGBoost save_model
- Mục đích: lưu mô hình sau khi huấn luyện để dùng lại cho lần dự đoán sau
- File đầu ra:
  - [backend/models_storage/bo_nao_dinh_gia.xgb](backend/models_storage/bo_nao_dinh_gia.xgb)
  - [backend/models_storage/spatial_scaler.pkl](backend/models_storage/spatial_scaler.pkl)

### Bước 6: Dùng model để dự đoán giá mới
- Công nghệ dùng: XGBoost, Python, pandas
- Mục đích: khi có dữ liệu bất động sản mới, hệ thống đưa feature vào mô hình để nhận kết quả giá dự đoán
- File liên quan: [backend/app/services/ml_service.py](backend/app/services/ml_service.py)
- Quy trình:
  - load model từ file .xgb
  - load scaler từ file .pkl
  - tạo feature đầu vào
  - gọi model.predict để lấy giá dự đoán

### Bước 7: Kết nối với LLM để tạo báo cáo
- Công nghệ dùng: Ollama + LangChain
- Mục đích: lấy kết quả từ XGBoost và đưa vào prompt cho LLM để viết báo cáo dễ hiểu cho người dùng
- File liên quan: [backend/app/agent_core/nodes.py](backend/app/agent_core/nodes.py)
- Cách hoạt động:
  - XGBoost trả về giá dự báo
  - giá này được đưa vào prompt cho LLM
  - LLM tổng hợp thành báo cáo thẩm định hoặc câu trả lời

---

## Ghi chú

- Mô hình LLM mặc định đang dùng Ollama với model `qwen2.5:1.5b`
- Đây là một demo nghiên cứu, nên có thể chưa tối ưu hoàn toàn cho môi trường production
- Một số tính năng vision/OCR sẽ phụ thuộc vào dữ liệu đầu vào và môi trường chạy

---

## Kết luận

Đây là một dự án mẫu rất phù hợp để minh họa cách kết hợp AI Agent, mô hình học máy, RAG và giao diện người dùng vào một ứng dụng thực tế cho ngành bất động sản.

Dữ liệu bất động sản được lấy từ MySQL thông qua Python và pandas. Sau khi tiền xử lý, các đặc trưng như tọa độ, diện tích, số tầng, nội thất và chiều rộng hẻm được chuyển thành các feature số để huấn luyện mô hình. Hệ thống sử dụng XGBoost để xây dựng mô hình dự đoán giá bất động sản, lưu model thành file .xgb và scaler thành file .pkl. Khi có dữ liệu mới, hệ thống đọc lại model này, đưa feature vào XGBoost để nhận kết quả dự đoán giá. Kết quả dự đoán sau đó được kết hợp với LLM (Ollama) để tạo báo cáo hoặc câu trả lời cho người dùng.

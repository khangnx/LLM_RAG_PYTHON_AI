import sys
import os

# Thêm đường dẫn để import từ Module 1
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from ai_training_engine.models.ocr_model import PinkBookOCR
from ai_training_engine.models.vision_detector import PropertyVisionAnalyzer

class VisionService:
    def __init__(self):
        try:
            self.ocr = PinkBookOCR()
            self.analyzer = PropertyVisionAnalyzer()
            print("Vision Service khởi tạo thành công.")
        except Exception as e:
            print(f"Lỗi khởi tạo Vision Service (Có thể thiếu model): {e}")
            self.ocr = None
            self.analyzer = None

    def process_media(self, file_bytes: bytes, filename: str) -> dict:
        """
        Nhận diện loại file và chạy các mô hình PyTorch tương ứng
        """
        result = {}
        
        if not self.ocr or not self.analyzer:
            return result
            
        ext = filename.split('.')[-1].lower()
        
        # Nếu là ảnh Sổ Hồng (thường là pdf, jpg, png), ta chạy OCR + Phân loại
        if ext in ['jpg', 'jpeg', 'png']:
            # Giả định chạy đồng thời cả OCR (tìm diện tích) và Vision Analyzer (tìm phân khúc nhà)
            # Thực tế có thể dựa vào user check box "Là Sổ Hồng" hoặc "Là Hình Nhà"
            ocr_data = self.ocr.extract_information(file_bytes)
            vision_data = self.analyzer.analyze_image(file_bytes)
            
            # Gộp kết quả
            result.update(ocr_data)
            result.update(vision_data)
            
        elif ext in ['mp4', 'avi', 'mov']:
            # Với video, lưu tạm ra đĩa rồi gọi hàm OpenCV xử lý frame
            temp_path = f"temp_video_{filename}"
            with open(temp_path, "wb") as f:
                f.write(file_bytes)
                
            vision_data = self.analyzer.analyze_video(temp_path)
            result.update(vision_data)
            
            # Xóa file tạm
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        return result

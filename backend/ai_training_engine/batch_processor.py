import os # Dùng để thao tác với hệ thống file, thư mục 
import sys # Dùng để thao tác với sys.path, import module từ thư mục cha

# Đảm bảo đường dẫn module
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from ai_training_engine.models.ocr_model import PinkBookOCR
from ai_training_engine.models.yolo_model import YoloBuildingDetector
from ai_training_engine.models.vit_model import ViTInteriorAnalyzer
from ai_training_engine.data_loader import insert_sales_data_to_db

class SalesBatchProcessor:
    def __init__(self, sales_upload_dir: str = None):
        if sales_upload_dir is None:
            # Lấy thư mục từ biến môi trường (Docker mount) hoặc mặc định /sales_uploads
            self.upload_dir = os.getenv("SALES_UPLOADS_DIR", "/sales_uploads")
        else:
            self.upload_dir = sales_upload_dir
            
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # Khởi tạo 3 model thị giác máy tính
        self.ocr_model = PinkBookOCR() # Dùng để trích xuất thông tin từ Sổ Hồng/Sổ Đỏ
        self.yolo_model = YoloBuildingDetector() # Dùng để nhận diện mặt tiền/kết cấu từ ảnh
        self.vit_model = ViTInteriorAnalyzer() # Dùng để phân tích chất lượng nội thất từ video

    def _route_and_process_file(self, file_path: str, filename: str, aggregated_data: dict):
        """
        Định tuyến file tới đúng Model Pytorch dựa vào quy tắc bối cảnh.
        """
        filename_lower = filename.lower()
        
        # 1. OCR (Sổ hồng/Sổ đỏ)
        if any(kw in filename_lower for kw in ['so', 'hong', 'do', 'phap_ly']) and \
           (filename_lower.endswith('.jpg') or filename_lower.endswith('.png')):
            ocr_result = self.ocr_model.extract_information(file_path)
            if ocr_result.get('address'):
                aggregated_data['address'] = ocr_result['address']
            if ocr_result.get('land_area'):
                aggregated_data['land_area'] = ocr_result['land_area']
                
        # 2. YOLO (Ảnh kết cấu, mặt tiền)
        elif filename_lower.endswith('.jpg') or filename_lower.endswith('.png'):
            yolo_result = self.yolo_model.extract_features(file_path)
            if yolo_result.get('floors'):
                aggregated_data['floors'] = yolo_result['floors']
            if yolo_result.get('alley_width'):
                # Lưu thêm alley_width nếu YOLO quét được (mặc dù prompt không yêu cầu nghiêm ngặt nhưng rất hữu ích cho DB)
                aggregated_data['alley_width'] = yolo_result['alley_width']
                
        # 3. ViT (Video)
        elif filename_lower.endswith('.mp4') or filename_lower.endswith('.avi') or filename_lower.endswith('.mov'):
            vit_result = self.vit_model.extract_score(file_path)
            if vit_result.get('interior_score'):
                aggregated_data['interior_score'] = vit_result['interior_score']

    def run_pipeline(self):
        """
        Quét qua toàn bộ thư mục, xử lý Isolated Session cho từng căn nhà.
        """
        print("="*50)
        print("🚀 BẮT ĐẦU CHẠY BATCH PROCESSOR (ON-PREMISE)")
        print(f"📁 Thư mục đang quét: {self.upload_dir}")
        print("="*50)
        
        for folder_name in os.listdir(self.upload_dir):
            folder_path = os.path.join(self.upload_dir, folder_name)
            
            # Bỏ qua nếu không phải thư mục hoặc đã xử lý rồi
            if not os.path.isdir(folder_path) or folder_name.startswith("PROCESSED_"):
                continue
                
            print(f"\n🏠 Đang xử lý căn nhà (Isolated Session): {folder_name}")
            
            # Khởi tạo Aggregated Data rỗng cho căn nhà này
            aggregated_data = {
                "property_code": folder_name,
                "address": f"Không có Sổ Hồng ({folder_name})",
                "land_area": 50.0,
                "floors": 1,
                "interior_score": 2,
                "data_source": "sales_upload",
                "is_verified": 1
            }
            
            # Duyệt từng file trong thư mục
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    self._route_and_process_file(file_path, filename, aggregated_data)
                    
            print(f"📊 Kết quả gom cụm JSON:\n{aggregated_data}")
            
            # Lưu vào Database
            success = insert_sales_data_to_db(aggregated_data)
            
            if success:
                # Đổi tên thư mục thành PROCESSED_...
                new_folder_name = f"PROCESSED_{folder_name}"
                new_folder_path = os.path.join(self.upload_dir, new_folder_name)
                try:
                    os.rename(folder_path, new_folder_path)
                    print(f"✅ Thành công! Đã đổi tên thư mục thành {new_folder_name}")
                except Exception as e:
                    print(f"⚠️ Lỗi đổi tên thư mục: {e}")

if __name__ == "__main__":
    processor = SalesBatchProcessor()
    processor.run_pipeline()

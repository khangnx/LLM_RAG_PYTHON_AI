import easyocr # Import thư viện EasyOCR để nhận diện ký tự từ hình ảnh, tức là bóc tách thông tin từ ảnh Sổ Hồng, anh Sổ Đỏ, ảnh Giấy chứng nhận quyền sử dụng đất, v.v.
import re # iMport thư viện re để sử dụng biểu thức chính quy (regular expressions) trong việc bóc tách thông tin từ văn bản.
import numpy as np # Import thư viện numpy để xử lý mảng và chuyển đổi dữ liệu hình ảnh từ bytes sang định dạng mà OpenCV có thể xử lý.
import cv2 # Import thư viện OpenCV để xử lý hình ảnh, ví dụ như giải mã dữ liệu hình ảnh từ bytes sang định dạng mà EasyOCR có thể nhận diện.

class PinkBookOCR:
    def __init__(self):
        # Khởi tạo EasyOCR với ngôn ngữ tiếng Việt
        print("Đang tải mô hình EasyOCR (Mất chút thời gian trong lần đầu)...")
        # gpu=False để tương thích tốt trên môi trường test. Bật gpu=True nếu có card rời.
        self.reader = easyocr.Reader(['vi'], gpu=False) 

    def extract_information(self, image_path_or_bytes):
        """
        Quét ảnh Sổ Hồng và bóc tách thông tin.
        """
        if isinstance(image_path_or_bytes, bytes):
            # Convert bytes to cv2 image
            nparr = np.frombuffer(image_path_or_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            img = image_path_or_bytes

        # Chạy OCR
        results = self.reader.readtext(img, detail=0)
        full_text = " ".join(results).lower()
        
        extracted_data = {
            "address": None,
            "land_area": None
        }

        # 1. Bóc tách Diện tích (Ví dụ tìm chuỗi "45 m2" hoặc "45,5 m2")
        area_match = re.search(r'diện tích[:\s]*([\d,\.]+)\s*m2', full_text)
        if area_match:
            try:
                extracted_data["land_area"] = float(area_match.group(1).replace(',', '.'))
            except ValueError:
                pass

        # 2. Bóc tách địa chỉ (Tìm sau chữ "địa chỉ thửa đất" hoặc "tại")
        address_match = re.search(r'(tại|địa chỉ thửa đất)[\s:]+(.+?)(thuộc|$|diện tích)', full_text)
        if address_match:
             extracted_data["address"] = address_match.group(2).strip()

        return extracted_data

import cv2
import torch
import torchvision.transforms as transforms
from torchvision.models import resnet18, ResNet18_Weights
from PIL import Image
import numpy as np

class PropertyVisionAnalyzer:
    def __init__(self):
        # Khởi tạo model phân loại (dùng ResNet18 như một ví dụ Baseline thay cho ViT/YOLO phức tạp)
        print("Đang tải mô hình PyTorch Vision Analyzer...")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Load pre-trained model
        self.model = resnet18(weights=ResNet18_Weights.DEFAULT)
        self.model = self.model.to(self.device)
        self.model.eval()
        
        # Transform chuẩn hóa ảnh
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def analyze_image(self, image_path_or_bytes):
        """
        Phân tích 1 bức ảnh để đánh giá chất lượng nội thất và số tầng.
        Trong thực tế, mô hình này cần được Fine-tune trên tập dữ liệu BĐS.
        """
        if isinstance(image_path_or_bytes, bytes):
            # Convert bytes to PIL Image
            nparr = np.frombuffer(image_path_or_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        else:
            img = Image.open(image_path_or_bytes).convert('RGB')
            
        input_tensor = self.transform(img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            output = self.model(input_tensor)
            
        # --- LOGIC MÔ PHỎNG (MOCK) KHI CHƯA CÓ TRỌNG SỐ FINE-TUNE ---
        # Tính toán ra 1 điểm số từ tensor để mô phỏng phân loại
        tensor_sum = torch.sum(output).item()
        
        # Mapping điểm số nội thất: 1 (Bình dân), 2 (Trung bình), 3 (Cao cấp)
        interior_score = (abs(int(tensor_sum)) % 3) + 1
        
        # Giả định phân tích số tầng (1-5)
        floors = (abs(int(tensor_sum * 10)) % 5) + 1
        
        return {
            "interior_score": interior_score,
            "floors": floors,
            "detected_interior": "High-end" if interior_score == 3 else ("Medium" if interior_score == 2 else "Low-end")
        }

    def analyze_video(self, video_path):
        """
        Trích xuất frame từ Video và phân tích tổng quan kiến trúc ngôi nhà.
        """
        cap = cv2.VideoCapture(video_path)
        frame_results = []
        
        count = 0
        while cap.isOpened() and count < 5: # Lấy 5 frame đại diện để tránh quá tải
            ret, frame = cap.read()
            if not ret:
                break
                
            # Phân tích frame này
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            res = self.analyze_image(img)
            frame_results.append(res)
            count += 1
            
        cap.release()
        
        if not frame_results:
            return {"interior_score": 2, "floors": 1, "detected_interior": "Medium"}
            
        # Tổng hợp kết quả (Voting/Averaging)
        avg_interior = int(np.mean([x["interior_score"] for x in frame_results]))
        max_floors = max([x["floors"] for x in frame_results])
        
        return {
            "interior_score": avg_interior,
            "floors": max_floors,
            "detected_interior": "High-end" if avg_interior == 3 else ("Medium" if avg_interior == 2 else "Low-end")
        }

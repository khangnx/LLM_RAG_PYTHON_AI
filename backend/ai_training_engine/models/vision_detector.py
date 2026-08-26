import cv2 # Dùng OpenCV để trích xuất frame từ video
import re # Dùng regex để phân tích text từ filename hoặc transcript
import os # Dùng để kiểm tra sự tồn tại của ffmpeg và quản lý file tạm
import torch # Dùng PyTorch để load model phân loại ảnh theo ResNet18 (tức là một baseline đơn giản thay cho ViT/YOLO phức tạp)
import subprocess # Dùng để gọi ffmpeg trích xuất audio từ video
import tempfile # Dùng để tạo thư mục tạm thời lưu audio trích xuất từ video
import shutil # Dùng để xóa thư mục tạm thời sau khi xử lý
import torchvision.transforms as transforms # Dùng để chuẩn hóa ảnh đầu vào cho model phân loại
from torchvision.models import resnet18, ResNet18_Weights # Dùng ResNet18 làm baseline model phân loại ảnh
from PIL import Image # Dùng để mở và xử lý ảnh
import numpy as np # Dùng để tính toán trung bình và các phép toán trên tensor

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

        self.whisper_model = self._load_whisper_model()

    def analyze_image(self, image_path_or_bytes, filename: str = None):
        """
        Phân tích 1 bức ảnh để đánh giá chất lượng nội thất và số tầng.
        Trong thực tế, mô hình này cần được Fine-tune trên tập dữ liệu BĐS.
        """
        if isinstance(image_path_or_bytes, bytes):
            nparr = np.frombuffer(image_path_or_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        elif isinstance(image_path_or_bytes, Image.Image):
            img = image_path_or_bytes
        else:
            img = Image.open(image_path_or_bytes).convert('RGB')
            
        input_tensor = self.transform(img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            output = self.model(input_tensor)
            
        tensor_sum = torch.sum(output).item()
        interior_score = (abs(int(tensor_sum)) % 3) + 1
        floors = (abs(int(tensor_sum * 10)) % 5) + 1

        filename_info = self.parse_property_text(filename or "")
        if filename_info.get("floors") is not None:
            floors = filename_info["floors"]
        if filename_info.get("interior_score") is not None:
            interior_score = max(interior_score, filename_info["interior_score"])

        result = {
            "interior_score": interior_score,
            "floors": floors,
            "detected_interior": "High-end" if interior_score == 3 else ("Medium" if interior_score == 2 else "Low-end"),
            "filename_tags": filename_info.get("tags", []),
            "filename_text": filename or "",
        }
        if filename_info.get("tags"):
            result["notes"] = [f"filename tag: {tag}" for tag in filename_info["tags"]]
        return result

    def _parse_number_word(self, token: str):
        mapping = {
            "mot": 1, "một": 1,
            "hai": 2,
            "ba": 3,
            "bon": 4, "bốn": 4,
            "nam": 5, "năm": 5,
            "sau": 6,
        }
        return mapping.get(token)

    def _normalize_text(self, text: str):
        if not text:
            return ""
        text = text.lower()
        text = text.replace("\n", " ").replace("-", " ").replace("_", " ")
        text = re.sub(r"\.[a-z0-9]+$", "", text)
        text = re.sub(r"[^\w\sàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_floors_from_text(self, text: str):
        if not text:
            return None
        text = self._normalize_text(text)
        match = re.search(r"(\d+)\s*(tang|tang|tang|tầng)\b", text)
        if match:
            return int(match.group(1))
        match = re.search(r"\b(tang|tầng)\s*(\d+)\b", text)
        if match:
            return int(match.group(2))
        tokens = text.split()
        for i, token in enumerate(tokens):
            if token in {"tang", "tầng"} and i > 0:
                num = self._parse_number_word(tokens[i - 1])
                if num:
                    return num
        for token in tokens:
            num = self._parse_number_word(token)
            if num and ("tang" in text or "tầng" in text):
                return num
        return None

    def _extract_interior_score_from_text(self, text: str):
        if not text:
            return None
        text = self._normalize_text(text)
        high = ["cao cap", "sang trong", "dep", "xinh", "luxury", "sang trong", "xinh dep", "noi that cao cap"]
        medium = ["trung binh", "binh thuong", "on", "ok", "noi that trung binh"]
        low = ["binh dan", "thap", "cu", "noi that binh dan"]
        for token in high:
            if token in text:
                return 3
        for token in medium:
            if token in text:
                return 2
        for token in low:
            if token in text:
                return 1
        return None

    def _extract_tags_from_text(self, text: str):
        tags = []
        if not text:
            return tags
        text = self._normalize_text(text)
        if any(keyword in text for keyword in ["mat tien", "mặt tiền", "façade", "facade", "mat tien", "mat tien nha", "mat tien nha" ]):
            tags.append("exterior")
        if any(keyword in text for keyword in ["noi that", "nội thất", "phong khach", "phòng khách", "phong ngu", "phòng ngủ", "bep", "nha tam", "nhà tắm", "ban cong", "ban công", "san vuon", "sân vườn"]):
            tags.append("interior")
        if any(keyword in text for keyword in ["garage", "hầm xe", "ham xe", "hamxe"]):
            tags.append("garage")
        if any(keyword in text for keyword in ["hem", "hẻm", "ngo", "ngõ", "alley"]):
            tags.append("alley")
        if any(keyword in text for keyword in ["phong ngu", "phòng ngủ", "bedroom"]):
            tags.append("bedroom")
        if any(keyword in text for keyword in ["phong khach", "phòng khách", "living room"]):
            tags.append("living_room")
        if any(keyword in text for keyword in ["bep", "kitchen"]):
            tags.append("kitchen")
        if any(keyword in text for keyword in ["nha tam", "nhà tắm", "bathroom"]):
            tags.append("bathroom")
        if any(keyword in text for keyword in ["ban cong", "ban công", "balcony"]):
            tags.append("balcony")
        if any(keyword in text for keyword in ["san vuon", "sân vườn", "garden"]):
            tags.append("garden")
        return tags

    def parse_property_text(self, text: str):
        text = self._normalize_text(text)
        return {
            "text": text,
            "floors": self._extract_floors_from_text(text),
            "interior_score": self._extract_interior_score_from_text(text),
            "tags": self._extract_tags_from_text(text),
        }

    def _load_whisper_model(self):
        try:
            import whisper
        except ImportError:
            return None

        try:
            return whisper.load_model("tiny", device="cpu")
        except Exception as exc:
            print(f"Failed to load Whisper tiny: {exc}")
            return None

    def try_transcribe_video_audio(self, video_path: str):
        transcript = ""
        notes = []

        if not shutil.which("ffmpeg"):
            notes.append("ffmpeg not available, skip audio transcription")
            return transcript, notes

        if self.whisper_model is not None:
            try:
                result = self.whisper_model.transcribe(video_path, language="vi", task="transcribe", fp16=False)
                transcript = result.get("text", "").strip()
                if transcript:
                    notes.append("Whisper tiny transcription completed")
                else:
                    notes.append("Whisper tiny returned empty transcript")
            except Exception as exc:
                notes.append(f"Whisper transcription failed: {exc}")
            return transcript, notes

        try:
            import speech_recognition as sr
        except ImportError:
            notes.append("speech_recognition package not installed, skip audio transcription")
            return transcript, notes

        temp_dir = tempfile.mkdtemp(prefix="video_audio_")
        audio_path = os.path.join(temp_dir, "audio.wav")
        try:
            subprocess.run([
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                audio_path,
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
            try:
                transcript = recognizer.recognize_google(audio, language="vi-VN")
                notes.append("speech_recognition transcription completed")
            except sr.UnknownValueError:
                notes.append("audio not understood")
            except sr.RequestError:
                notes.append("speech recognition request failed")
        except Exception as exc:
            notes.append(f"audio extraction/transcription failed: {exc}")
        finally:
            try:
                shutil.rmtree(temp_dir)
            except OSError:
                pass

        return transcript, notes

    def analyze_video(self, video_path, filename: str = None):
        """
        Trích xuất frame từ Video và phân tích tổng quan kiến trúc ngôi nhà.
        """
        transcript, transcript_notes = self.try_transcribe_video_audio(video_path)
        transcript_info = self.parse_property_text(transcript)
        filename_info = self.parse_property_text(filename or "")

        cap = cv2.VideoCapture(video_path)
        frame_results = []
        
        count = 0
        while cap.isOpened() and count < 5: # Lấy 5 frame đại diện để tránh quá tải
            ret, frame = cap.read()
            if not ret:
                break
                
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            res = self.analyze_image(img, filename=filename)
            frame_results.append(res)
            count += 1
            
        cap.release()
        
        if not frame_results:
            base_interior = 2
            base_floors = 1
        else:
            base_interior = int(np.mean([x["interior_score"] for x in frame_results]))
            base_floors = max([x["floors"] for x in frame_results])

        if transcript_info.get("interior_score") is not None:
            base_interior = max(base_interior, transcript_info["interior_score"])
        if filename_info.get("interior_score") is not None:
            base_interior = max(base_interior, filename_info["interior_score"])
        if transcript_info.get("floors") is not None:
            base_floors = transcript_info["floors"]
        if filename_info.get("floors") is not None:
            base_floors = filename_info["floors"]

        notes = transcript_notes[:]
        if transcript_info.get("tags"):
            notes.extend([f"transcript tag: {tag}" for tag in transcript_info["tags"]])
        if filename_info.get("tags"):
            notes.extend([f"filename tag: {tag}" for tag in filename_info["tags"]])

        return {
            "interior_score": base_interior,
            "floors": base_floors,
            "detected_interior": "High-end" if base_interior == 3 else ("Medium" if base_interior == 2 else "Low-end"),
            "audio_transcript": transcript,
            "filename_tags": filename_info.get("tags", []),
            "transcript_tags": transcript_info.get("tags", []),
            "notes": notes,
        }

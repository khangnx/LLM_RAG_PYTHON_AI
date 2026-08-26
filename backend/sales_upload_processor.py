"""
sales_upload_processor.py

Quét các thư mục con trong `sales_uploads/`, chịu trách nhiệm:
- Giữ phiên xử lý cô lập cho từng folder
- Chuyển file vào pipeline OCR / object detection / video analysis
- Gom kết quả thành payload JSON chuẩn
- Gọi `persist_payload` để lưu vào MySQL ingest
- Đổi tên thư mục gốc thành `PROCESSED_{folder_name}` sau khi xử lý xong
"""

import os
import re
import time
import logging
from typing import List, Dict, Optional

from real_estate_persister import persist_payload
from ai_training_engine.models.ocr_model import PinkBookOCR
from ai_training_engine.models.vision_detector import PropertyVisionAnalyzer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

IMAGE_EXTS = {"jpg", "jpeg", "png"}
VIDEO_EXTS = {"mp4", "avi", "mov"}
LEGAL_KEYWORDS = ["so", "hong", "do", "phap_ly", "phaply"]
ALLEY_KEYWORDS = ["ngõ", "hẻm", "hem", "alley"]
GARAGE_KEYWORDS = ["hầm xe", "hamxe", "garage"]


def normalize_filename(filename: str) -> str:
    return filename.lower().replace(" ", "_")


class SalesUploadProcessor:
    def __init__(self, sales_dir: Optional[str] = None):
        self.sales_dir = sales_dir or os.getenv("SALES_UPLOADS_DIR", "/sales_uploads")
        if not os.path.exists(self.sales_dir):
            os.makedirs(self.sales_dir, exist_ok=True)

        self.ocr = PinkBookOCR()
        self.analyzer = PropertyVisionAnalyzer()
        logger.info(f"SalesUploadProcessor đang sử dụng thư mục: {self.sales_dir}")

    def process_all_folders(self) -> List[Dict]:
        """Xử lý tất cả thư mục con chưa được đánh dấu PROCESSED_."""
        entries = sorted(os.listdir(self.sales_dir))
        results = []
        for entry in entries:
            folder_path = os.path.join(self.sales_dir, entry)
            if not os.path.isdir(folder_path):
                continue
            if entry.startswith("PROCESSED_"):
                logger.info(f"Bỏ qua thư mục đã xử lý: {entry}")
                continue
            results.append(self.process_folder(entry))
        return results

    def process_folder(self, folder_name: str) -> Dict:
        """Xử lý một thư mục con đại diện cho một bất động sản duy nhất."""
        folder_path = os.path.join(self.sales_dir, folder_name)
        if not os.path.isdir(folder_path):
            raise FileNotFoundError(f"Folder không tồn tại: {folder_path}")

        logger.info(f"Bắt đầu xử lý folder: {folder_name}")
        extracted = {
            "address": None,
            "land_area": None,
            "floors": None,
            "interior_score": None,
        }
        interior_scores = []
        floor_counts = []
        detected_notes = []
        filename_tags = []
        processed_files = []
        skipped_files = []
        filename_texts = []
        audio_transcripts = []

        for entry in sorted(os.listdir(folder_path)):
            file_path = os.path.join(folder_path, entry)
            if not os.path.isfile(file_path):
                continue

            ext = entry.rsplit(".", 1)[-1].lower() if "." in entry else ""
            normalized = normalize_filename(entry)

            if ext not in IMAGE_EXTS and ext not in VIDEO_EXTS:
                logger.info(f"  - Skip unsupported file: {entry}")
                skipped_files.append({"file": entry, "reason": "unsupported extension"})
                continue

            # 1. Ảnh Sổ Hồng/Sổ Đỏ: OCR pháp lý
            if ext in IMAGE_EXTS and any(keyword in normalized for keyword in LEGAL_KEYWORDS):
                logger.info(f"  - OCR legal image: {entry}")
                data = self.ocr.extract_information(file_path)
                processed_files.append({"file": entry, "type": "legal_image", "result": data})
                if data.get("address") and not extracted["address"]:
                    extracted["address"] = data["address"]
                if data.get("land_area") and not extracted["land_area"]:
                    extracted["land_area"] = data["land_area"]
                if not data.get("address") and not data.get("land_area"):
                    skipped_files.append({"file": entry, "reason": "legal OCR found no address or land area"})
                continue

            # 2. Ảnh kết cấu/mặt tiền: object detection / image analysis
            if ext in IMAGE_EXTS:
                logger.info(f"  - Image analysis: {entry}")
                data = self.analyzer.analyze_image(file_path, filename=entry)
                processed_files.append({"file": entry, "type": "property_image", "result": data})
                if data.get("interior_score") is not None:
                    interior_scores.append(data["interior_score"])
                if data.get("floors") is not None:
                    floor_counts.append(data["floors"])

                filename_texts.append(entry)
                if data.get("filename_tags"):
                    filename_tags.extend(data["filename_tags"])
                    detected_notes.extend([f"filename tag: {tag}" for tag in data["filename_tags"]])
                if any(keyword in normalized for keyword in GARAGE_KEYWORDS):
                    detected_notes.append("Detected potential garage/hầm xe")
                if any(keyword in normalized for keyword in ALLEY_KEYWORDS):
                    detected_notes.append("Detected alley-related image")
                continue

            # 3. Video nội thất: Vision Transformer analysis
            if ext in VIDEO_EXTS:
                logger.info(f"  - Video analysis: {entry}")
                data = self.analyzer.analyze_video(file_path, filename=entry)
                processed_files.append({"file": entry, "type": "video", "result": data})
                if data.get("interior_score") is not None:
                    interior_scores.append(data["interior_score"])
                if data.get("floors") is not None:
                    floor_counts.append(data["floors"])
                filename_texts.append(entry)
                if data.get("audio_transcript"):
                    audio_transcripts.append(data["audio_transcript"])
                if data.get("filename_tags"):
                    filename_tags.extend(data["filename_tags"])
                    detected_notes.extend([f"filename tag: {tag}" for tag in data["filename_tags"]])
                if data.get("transcript_tags"):
                    detected_notes.extend([f"transcript tag: {tag}" for tag in data["transcript_tags"]])
                if data.get("notes"):
                    detected_notes.extend(data["notes"])
                continue

            logger.info(f"  - Bỏ qua tệp còn lại: {entry}")
            skipped_files.append({"file": entry, "reason": "unknown image/video processing path"})

        # Tổng hợp kết quả
        if floor_counts:
            extracted["floors"] = max(floor_counts)
        if interior_scores:
            extracted["interior_score"] = int(round(sum(interior_scores) / len(interior_scores)))
        if extracted["interior_score"] is None:
            extracted["interior_score"] = 1
        if extracted["floors"] is None:
            extracted["floors"] = 1

        payload = {
            "property_code": folder_name,
            "address": extracted["address"] or "",
            "land_area": float(extracted["land_area"]) if extracted["land_area"] is not None else None,
            "floors": int(extracted["floors"]),
            "interior_score": int(extracted["interior_score"]),
            "filename_text": "; ".join(filename_texts) if filename_texts else "",
            "filename_tags": ", ".join(sorted(set(filename_tags))) if filename_tags else "",
            "audio_transcript": " || ".join(audio_transcripts) if audio_transcripts else "",
            "notes": "; ".join(detected_notes) if detected_notes else "",
            "data_source": "sales_upload",
            "is_verified": 1,
        }

        result = persist_payload(folder_name, payload)
        logger.info(f"  ⏺ Lưu payload cho folder '{folder_name}' với ingest_id={result.get('ingest_id')}")

        new_folder_path = self._rename_processed_folder(folder_path, folder_name)
        logger.info(f"  ✅ Đổi tên folder {folder_name} -> {os.path.basename(new_folder_path)}")

        return {
            "folder_name": folder_name,
            "status": "processed",
            "payload": payload,
            "ingest_id": result.get("ingest_id"),
            "processed_folder": os.path.basename(new_folder_path),
            "notes": detected_notes,
            "processed_files": processed_files,
            "skipped_files": skipped_files,
        }

    def _rename_processed_folder(self, folder_path: str, folder_name: str) -> str:
        parent_dir = os.path.dirname(folder_path)
        new_name = f"PROCESSED_{folder_name}"
        new_path = os.path.join(parent_dir, new_name)
        if os.path.exists(new_path):
            suffix = int(time.time())
            new_path = os.path.join(parent_dir, f"{new_name}_{suffix}")
        os.rename(folder_path, new_path)
        return new_path


if __name__ == "__main__":
    processor = SalesUploadProcessor()
    summary = processor.process_all_folders()
    print({"processed_count": len(summary), "results": summary})

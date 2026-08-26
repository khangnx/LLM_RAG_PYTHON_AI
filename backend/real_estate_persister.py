"""
real_estate_persister.py

Module chịu trách nhiệm ghi payload đã trích xuất vào bảng ingest
và cập nhật các trường tương ứng trong `real_estate_dataset` khi có
`property_code` khớp.

Hành vi:
- Lưu JSON payload gốc vào `real_estate_dataset_ingest` (ORM)
- Nếu tồn tại `real_estate_dataset.property_code` khớp, cập nhật các
  trường khả dụng: `land_area` -> `land_area`, `floors` -> `total_floors`,
  `address` -> `street_name`.
- Toàn bộ hoạt động nằm trong một transaction (commit/rollback chung).

Ghi chú: Không cố gắng insert một dòng mới vào `real_estate_dataset` nếu
các cột NOT NULL bắt buộc không được cung cấp bởi payload. Chỉ update
nếu row đã tồn tại.
"""

import json
from sqlalchemy import text
from database import SessionLocal, engine, Base, RealEstateDataset


def ensure_tables():
    """Tạo bảng ingest nếu chưa tồn tại."""
    Base.metadata.create_all(bind=engine)


def persist_payload(folder_name: str, payload: dict) -> dict:
    """
    Persist a single extracted payload.

    Args:
        folder_name: tên thư mục (sử dụng làm property_code nếu payload không có).
        payload: dict chứa keys như `address`, `land_area`, `floors`, `interior_score`,
                 `data_source`, `is_verified`, optional `property_code`.

    Returns:
        dict with status and inserted ingest id.
    """
    property_code = payload.get("property_code") or folder_name
    payload_json = json.dumps(payload, ensure_ascii=False)

    session = SessionLocal()
    try:
        with session.begin():
            ingest = RealEstateDatasetIngest(
                property_code=property_code,
                payload=payload_json,
                address=payload.get("address"),
                land_area=payload.get("land_area"),
                floors=payload.get("floors"),
                interior_score=payload.get("interior_score"),
                data_source=payload.get("data_source", "sales_upload"),
                is_verified=bool(payload.get("is_verified", 0)),
            )
            session.add(ingest)

            # Nếu có property_code, thử cập nhật row tương ứng trong bảng chính
            update_fields = {}
            params = {"property_code": property_code}

            if payload.get("land_area") is not None:
                update_fields["land_area"] = payload.get("land_area")
                params["land_area"] = payload.get("land_area")

            if payload.get("floors") is not None:
                update_fields["total_floors"] = payload.get("floors")
                params["total_floors"] = payload.get("floors")

            if payload.get("address"):
                update_fields["street_name"] = payload.get("address")
                params["street_name"] = payload.get("address")

            if update_fields:
                set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
                sql = text(f"UPDATE real_estate_dataset SET {set_clause} WHERE property_code = :property_code")
                session.execute(sql, params)

        # At this point transaction committed
        return {"status": "ok", "ingest_id": ingest.id}

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    ensure_tables()
    print("real_estate_persister: tables ensured")

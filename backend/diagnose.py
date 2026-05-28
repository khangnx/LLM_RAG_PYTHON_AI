import os
import chromadb

print("🔍 --- BẮT ĐẦU TRUY TÌM VỊ TRÍ ĐĂNG KÝ CHROMADB THỰC TẾ ---")

def find_chroma_db_files():
    found_paths = []
    # Quét toàn bộ các thư mục bên trong container Backend
    for root, dirs, files in os.walk("/"):
        # Tránh quét các thư mục hệ thống của Linux để tiết kiệm thời gian
        if any(p in root for p in ["/proc", "/sys", "/dev", "/var/lib/docker"]):
            continue
        if "chroma.sqlite3" in files:
            full_path = os.path.join(root, "chroma.sqlite3")
            found_paths.append(root)
            print(f"📍 Phát hiện file dữ liệu ChromaDB tại: {full_path}")
    return found_paths

# Thực hiện quét file
db_folders = find_chroma_db_files()

if not db_folders:
    print("\n❌ CẢNH BÁO: Không tìm thấy bất kỳ file vật lý nào của ChromaDB trên ổ đĩa!")
    print("👉 Kết luận: Code Python của bạn đang chạy ChromaDB hoàn toàn trên RAM (In-Memory).")
    print("             Khi tắt Docker hoặc khởi động lại, toàn bộ dữ liệu băm nhỏ sẽ biến mất.")
else:
    print(f"\n✅ Đã tìm thấy {len(db_folders)} đường dẫn chứa dữ liệu thực tế.")
    for folder in db_folders:
        try:
            print(f"\n🔄 Đang thử đọc dữ liệu tại thư mục: {folder}")
            client = chromadb.PersistentClient(path=folder)
            collections = client.list_collections()
            print(f"   -> Số lượng Collections tìm thấy: {len(collections)}")
            for col in collections:
                print(f"      + Collection: {col.name} ({client.get_collection(name=col.name).count()} chunks)")
        except Exception as e:
            print(f"   -> Không thể đọc folder này: {str(e)}")
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

class GeoService:
    def __init__(self):
        # Dùng Nominatim (OpenStreetMap) làm mặc định cho Geocoding
        self.geolocator = Nominatim(user_agent="multimodal_real_estate_agent")

    def get_coordinates(self, address: str) -> tuple:
        """
        Dịch chuỗi địa chỉ văn bản (VD: "Lê Văn Sỹ, Phú Nhuận, Hồ Chí Minh")
        thành cặp tọa độ (latitude, longitude).
        """
        try:
            # Gắn thêm Hồ Chí Minh, Việt Nam để tăng độ chính xác
            full_address = f"{address}, Hồ Chí Minh, Việt Nam"
            location = self.geolocator.geocode(full_address, timeout=10)
            
            if location:
                return (location.latitude, location.longitude)
            
            # Fallback nếu không tìm thấy, trả về tọa độ trung tâm TP.HCM
            return (10.7769, 106.7009) 
            
        except GeocoderTimedOut:
            return (10.7769, 106.7009)
        except Exception as e:
            print(f"Lỗi Geocoding: {e}")
            return (10.7769, 106.7009)

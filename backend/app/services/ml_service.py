import os
import xgboost as xgb
import joblib
import pandas as pd
import numpy as np
import sys

# Thêm đường dẫn để import preprocessor từ Module 1
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)
    
from ai_training_engine.preprocessor import SpatialPreprocessor

class MLPredictorService:
    def __init__(self):
        models_dir = os.path.join(backend_dir, "models_storage")
        model_path = os.path.join(models_dir, "bo_nao_dinh_gia.xgb")
        scaler_path = os.path.join(models_dir, "spatial_scaler.pkl")
        
        self.model = None
        self.scaler = None
        self.preprocessor = SpatialPreprocessor(models_dir=models_dir)
        
        # Load mô hình XGBoost
        if os.path.exists(model_path):
            self.model = xgb.XGBRegressor()
            self.model.load_model(model_path)
            print("Đã nạp thành công mô hình định giá XGBoost vào RAM.")
        else:
            print("CẢNH BÁO: Không tìm thấy bo_nao_dinh_gia.xgb.")
            
        # Load Scaler
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            
    def predict_price(self, latitude, longitude, land_area, floors, interior_score, alley_width=3.0):
        """
        Dự báo giá nhà dựa trên tọa độ và thông số đầu vào.
        """
        if self.model is None:
            return 0.0
            
        # 1. Tính toán Feature Engineering bằng KNN
        # Giả lập preprocessor đã có reference_data (Trong thực tế cần save/load thêm reference_data của preprocessor)
        # Tạm thời sinh giá KNN ngẫu nhiên có logic để test nếu preprocessor chưa sẵn sàng
        neighbor_price = self.preprocessor.transform_inference(latitude, longitude)
        if neighbor_price == 0.0:
            neighbor_price = 150.0 # Tạm gán 150 triệu/m2 nếu lỗi
            
        # 2. Xây dựng DataFrame đầu vào
        df_input = pd.DataFrame([{
            'latitude': latitude,
            'longitude': longitude,
            'land_area': land_area,
            'neighbor_avg_price_per_m2': neighbor_price,
            'floors': floors,
            'interior_score': interior_score,
            'alley_width': alley_width
        }])
        
        # 3. Scale dữ liệu
        features = ['latitude', 'longitude', 'land_area', 'neighbor_avg_price_per_m2', 'floors', 'interior_score', 'alley_width']
        if self.scaler:
            df_input[features] = self.scaler.transform(df_input[features])
            
        # 4. Dự báo
        predicted_price = self.model.predict(df_input)[0]
        
        # Làm tròn 2 chữ số thập phân
        return round(float(predicted_price), 2)

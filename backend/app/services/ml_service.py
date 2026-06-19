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
            
        # 1. Tính toán neighbor_avg_price_per_m2 qua KNN
        neighbor_price = self.preprocessor.transform_inference(latitude, longitude)
        if neighbor_price == 0.0:
            neighbor_price = 150.0  # Fallback nếu KNN chưa fit

        # 2. Xây dựng DataFrame với toàn bộ feature có thể có
        df_input = pd.DataFrame([{
            'latitude': latitude,
            'longitude': longitude,
            'land_area': land_area,
            'neighbor_avg_price_per_m2': neighbor_price,
            'floors': floors,
            'interior_score': interior_score,
            'alley_width': alley_width
        }])

        # 3. Chỉ scale những cột mà scaler đã được fit (tránh ValueError feature mismatch)
        if self.scaler:
            try:
                # Lấy danh sách cột mà scaler biết (từ lúc training)
                scaler_features = list(self.scaler.feature_names_in_)
            except AttributeError:
                # sklearn cũ không có feature_names_in_, dùng toàn bộ cột có trong df
                scaler_features = [c for c in df_input.columns]

            # Chỉ lấy cột nào vừa có trong df_input vừa có trong scaler
            cols_to_scale = [c for c in scaler_features if c in df_input.columns]
            df_input[cols_to_scale] = self.scaler.transform(df_input[cols_to_scale])

        # 4. Dự báo — chỉ đưa vào model những cột model biết
        try:
            model_features = self.model.get_booster().feature_names
            if model_features:
                available = [c for c in model_features if c in df_input.columns]
                predicted_price = self.model.predict(df_input[available])[0]
            else:
                predicted_price = self.model.predict(df_input)[0]
        except Exception:
            predicted_price = self.model.predict(df_input)[0]

        return round(float(predicted_price), 2)


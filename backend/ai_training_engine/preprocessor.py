import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
import joblib
import os

class SpatialPreprocessor:
    def __init__(self, k_neighbors=5, models_dir=None):
        self.k_neighbors = k_neighbors
        self.scaler = StandardScaler()
        
        # Đường dẫn thư mục chia sẻ models_storage
        if models_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = os.path.dirname(current_dir)
            self.models_dir = os.path.join(backend_dir, "models_storage")
        else:
            self.models_dir = models_dir
            
        os.makedirs(self.models_dir, exist_ok=True)
        self.scaler_path = os.path.join(self.models_dir, "spatial_scaler.pkl")
        
        # Biến KNN để tính toán nhanh sau này
        self.knn_model = NearestNeighbors(n_neighbors=self.k_neighbors, algorithm='ball_tree')
        self.reference_data = None
        self.is_fitted = False

    def calculate_price_per_m2(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tạo cột giá trên mét vuông (tỷ/m2)"""
        df = df.copy()
        # Xử lý tránh chia cho 0
        valid_area = df['land_area'].replace(0, np.nan)
        df['price_per_m2'] = df['raw_price_billion'] / valid_area
        return df

    def fit_transform_spatial_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Dùng cho quá trình Huấn Luyện (Training).
        Tính giá trung bình khu vực (neighbor_avg_price_per_m2) dựa vào K giao dịch gần nhất
        """
        if df.empty or 'latitude' not in df.columns or 'longitude' not in df.columns:
            return df
            
        df = self.calculate_price_per_m2(df)
        
        # Chỉ lấy những bản ghi có tọa độ hợp lệ
        valid_coords = df.dropna(subset=['latitude', 'longitude', 'price_per_m2'])
        if len(valid_coords) < self.k_neighbors:
            # Không đủ data để tính KNN
            df['neighbor_avg_price_per_m2'] = df.get('price_per_m2', 0).mean()
            return df

        coords = valid_coords[['latitude', 'longitude']].values
        prices = valid_coords['price_per_m2'].values
        
        # Lưu lại tập reference để sau này Inference dùng
        self.reference_data = {
            'coords': coords,
            'prices': prices
        }
        
        # Fit thuật toán KNN
        self.knn_model.fit(coords)
        
        # Tìm k điểm gần nhất cho MỖI dòng (k bao gồm chính nó)
        distances, indices = self.knn_model.kneighbors(coords)
        
        # Tính giá trung bình m2 của các điểm lân cận
        avg_prices = []
        for i in range(len(coords)):
            # Lấy mảng giá của các điểm lân cận tương ứng
            neighbor_prices = prices[indices[i]]
            avg_prices.append(np.mean(neighbor_prices))
            
        # Gán lại kết quả vào dataframe
        df.loc[valid_coords.index, 'neighbor_avg_price_per_m2'] = avg_prices
        
        # Điền các dòng thiếu tọa độ bằng giá trung bình toàn cục
        global_avg = valid_coords['price_per_m2'].mean()
        df['neighbor_avg_price_per_m2'] = df['neighbor_avg_price_per_m2'].fillna(global_avg)
        
        self.is_fitted = True
        return df

    def transform_inference(self, latitude: float, longitude: float) -> float:
        """
        Dùng cho API khi dự đoán giá trị mới.
        Tính neighbor_avg_price_per_m2 cho một điểm hoàn toàn mới dựa trên lịch sử đã học.
        """
        if not self.is_fitted or self.reference_data is None:
            return 0.0
            
        distances, indices = self.knn_model.kneighbors([[latitude, longitude]])
        neighbor_prices = self.reference_data['prices'][indices[0]]
        return np.mean(neighbor_prices)

    def normalize_features(self, df: pd.DataFrame, continuous_cols: list, is_training=True) -> pd.DataFrame:
        """
        Chuẩn hóa các cột số liên tục (StandardScaler)
        """
        df_scaled = df.copy()
        
        # Lọc ra các cột thực sự tồn tại
        cols_to_scale = [col for col in continuous_cols if col in df_scaled.columns]
        
        if not cols_to_scale:
            return df_scaled
            
        # Xử lý NaN trước khi chuẩn hóa (điền 0 hoặc trung bình)
        df_scaled[cols_to_scale] = df_scaled[cols_to_scale].fillna(0)
            
        if is_training:
            df_scaled[cols_to_scale] = self.scaler.fit_transform(df_scaled[cols_to_scale])
            # Lưu Rule chuẩn hóa ra file physical
            joblib.dump(self.scaler, self.scaler_path)
            print(f"Đã lưu Spatial Scaler tại {self.scaler_path}")
        else:
            # Quá trình suy luận (Inference), load file scaler
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
                df_scaled[cols_to_scale] = self.scaler.transform(df_scaled[cols_to_scale])
            else:
                print("Cảnh báo: Không tìm thấy file spatial_scaler.pkl")
                
        return df_scaled

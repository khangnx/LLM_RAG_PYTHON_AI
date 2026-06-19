from data_loader import load_real_estate_data
from preprocessor import SpatialPreprocessor
from xgboost_trainer import SpatialXGBoostTrainer

def run_training_pipeline():
    print("==================================================")
    print("   BẮT ĐẦU PIPELINE HUẤN LUYỆN MULTIMODAL AI      ")
    print("==================================================\n")
    
    # 1. Tải dữ liệu
    df = load_real_estate_data()
    
    if df.empty:
        print("[LỖI] Dữ liệu trống. Không thể huấn luyện.")
        return
        
    print("\n[BƯỚC 1] Tiền xử lý dữ liệu và Feature Engineering (KNN Không Gian)")
    preprocessor = SpatialPreprocessor()
    
    # Tính feature KNN: neighbor_avg_price_per_m2
    df = preprocessor.fit_transform_spatial_features(df)
    
    # Định nghĩa các biến Features cần thiết
    feature_cols = [
        'latitude', 'longitude', 'land_area', 
        'neighbor_avg_price_per_m2', 'floors', 
        'interior_score', 'alley_width'
    ]
    
    # Lọc bỏ các bản ghi bị NaN ở Target
    if 'raw_price_billion' not in df.columns:
        print("[LỖI] Thiếu cột giá mục tiêu: raw_price_billion")
        return
        
    df = df.dropna(subset=['raw_price_billion'])
    
    # 2. Chuẩn hóa dữ liệu số liên tục
    print("\n[BƯỚC 2] Chuẩn hóa dữ liệu (StandardScaler)")
    # Tất cả các feature ở đây đều là số liên tục, cần được scale
    df_scaled = preprocessor.normalize_features(df, feature_cols, is_training=True)
    
    # Chuẩn bị X và y
    # Lấy những cột feature có tồn tại trong df
    actual_features = [col for col in feature_cols if col in df_scaled.columns]
    X = df_scaled[actual_features]
    y = df_scaled['raw_price_billion']
    
    # 3. Huấn luyện
    print("\n[BƯỚC 3] Huấn luyện Mô hình XGBoost")
    trainer = SpatialXGBoostTrainer()
    trainer.train_and_evaluate(X, y)
    
    print("\n==================================================")
    print("       PIPELINE HUẤN LUYỆN ĐÃ HOÀN TẤT            ")
    print("==================================================")

if __name__ == "__main__":
    run_training_pipeline()

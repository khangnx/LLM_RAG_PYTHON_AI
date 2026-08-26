# File này chứa class SpatialXGBoostTrainer, dùng để huấn luyện mô hình XGBoost Regressor dựa trên dữ liệu đã được tiền xử lý (preprocessed data). Mục tiêu là dự đoán giá trị bất động sản dựa vào các đặc trưng đầu vào.
import os # Dùng để thao tác với hệ thống file, thư mục
import xgboost as xgb # Dùng để huấn luyện mô hình XGBoost Regressor
from sklearn.model_selection import train_test_split # Dùng để chia dữ liệu thành tập huấn luyện và tập kiểm tra
from sklearn.metrics import mean_squared_error, mean_absolute_error # Dùng để đánh giá hiệu suất mô hình (MSE, MAE)

class SpatialXGBoostTrainer:
    def __init__(self, models_dir=None):
        if models_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = os.path.dirname(current_dir)
            self.models_dir = os.path.join(backend_dir, "models_storage")
        else:
            self.models_dir = models_dir
            
        os.makedirs(self.models_dir, exist_ok=True)
        self.model_path = os.path.join(self.models_dir, "bo_nao_dinh_gia.xgb")
        
        # Khởi tạo mô hình XGBoost Regressor
        self.model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=200,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            early_stopping_rounds=20
        )

    def train_and_evaluate(self, X, y):
        """
        Chia dữ liệu, huấn luyện mô hình và đánh giá
        """
        print("Bắt đầu chia tập Train/Test (80/20)...")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        print(f"Kích thước tập huấn luyện: {len(X_train)} mẫu.")
        print("Đang huấn luyện mô hình XGBoost...")
        
        # Huấn luyện
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        # Đánh giá
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        
        print("\n--- KẾT QUẢ ĐÁNH GIÁ ---")
        print(f"Mean Absolute Error (MAE): {mae:.4f} Tỷ VNĐ (Sai số trung bình)")
        print(f"Root Mean Squared Error (RMSE): {mse**0.5:.4f} Tỷ VNĐ")
        
        # Lưu mô hình
        self.model.save_model(self.model_path)
        print(f"\n[THÀNH CÔNG] Đã lưu Bộ Não Định Giá tại: {self.model_path}")
        
        return self.model

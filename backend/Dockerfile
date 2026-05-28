# Sử dụng bản thiết kế Python chính thức, gọn nhẹ
FROM python:3.10-slim

# Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Cài đặt các tool hệ thống cần thiết (nếu có thư viện cần compile)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy file danh sách thư viện vào trước để tận dụng Docker cache
COPY ./requirements.txt /app/requirements.txt

# Cài đặt các thư viện Python
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy toàn bộ mã nguồn backend vào container
COPY . /app

# Mở cổng 8000 để bên ngoài gọi API
EXPOSE 8000

# Lệnh mặc định để khởi chạy FastAPI Server bằng Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
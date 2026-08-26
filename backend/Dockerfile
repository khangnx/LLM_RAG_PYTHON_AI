FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    git \
    ffmpeg \
    rustc \
    cargo \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    libxrender1 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app/requirements.txt

# Nâng cấp bộ tool build tiêu chuẩn
RUN pip install --no-cache-dir --upgrade pip "setuptools<70.0.0" wheel

# Cài đặt whisper riêng trước để tránh làm rối resolver của pip
RUN pip install --no-cache-dir openai-whisper

# Cài đặt toàn bộ requirements chính (không dùng --no-build-isolation)
RUN pip install --no-cache-dir -r /app/requirements.txt

# Preload EasyOCR model
RUN python -c "import shutil, os; cache=os.path.expanduser('~/.EasyOCR'); shutil.rmtree(cache, ignore_errors=True); from easyocr import Reader; Reader(['vi'], gpu=False)"

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
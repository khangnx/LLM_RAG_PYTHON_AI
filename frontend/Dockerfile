# Sử dụng NodeJS bản ổn định
FROM node:20-alpine

# Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Copy các file cấu hình package vào trước
COPY package*.json ./

# Cài đặt toàn bộ dependencies cho dự án VueJS
RUN npm install

# Copy toàn bộ mã nguồn frontend vào
COPY . .

# Mở cổng 5173 của Vite
EXPOSE 5173

# Chạy server development của Vite, cấu hình --host để truy cập được từ bên ngoài container
CMD ["npm", "run", "dev", "--", "--host"]
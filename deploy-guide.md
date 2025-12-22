# 🚀 Hướng dẫn triển khai Voicely Backend lên Server

## 📋 Yêu cầu
- Server có Docker và Docker Compose đã cài đặt
- SSH access vào server
- Domain/IP công khai (nếu cần SSL)

---

## 🐳 **Cách 1: Triển khai với Docker Compose (Khuyến nghị)**

### Bước 1: Chuẩn bị trên máy local

1. **Tạo file `.env` từ template:**
```bash
cp .env.example .env
```

2. **Chỉnh sửa file `.env`** với thông tin thực tế:
```bash
# Đổi password và secret keys thành giá trị bảo mật
POSTGRES_PASSWORD=your_strong_password_here
JWT_SECRET_KEY=your_jwt_secret_key_min_32_chars
JWT_REFRESH_SECRET_KEY=your_refresh_secret_key_min_32_chars
```

3. **Đảm bảo có file GCS credentials:**
   - `voicely-474001-842320946404.json` (hoặc file credentials khác)

### Bước 2: Đóng gói và upload lên server

**Option A: Upload trực tiếp qua rsync/scp**
```bash
# Nén toàn bộ project (loại trừ file không cần thiết)
# tar --exclude='__pycache__' \
#     --exclude='*.pyc' \
#     --exclude='.git' \
#     --exclude='venv' \
#     --exclude='uploads' \
#     --exclude='tests' \
#     -czf voicely-be.tar.gz .

# From AIRecorder directory
tar --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='uploads' \
    --exclude='tests' \
    -czf voicely-be.tar.gz Voicely-BE/

# Sau đó copy thư mục rar rồi bỏ vào Voicely-BE

# Upload lên server
# scp voicely-be.tar.gz user@your-server-ip:/home/user/
scp -P 10004 voicely-be.tar.gz root@31.192.234.183:/root/

# SSH vào server và giải nén
ssh user@your-server-ip
cd /home/user
tar -xzf voicely-be.tar.gz -C voicely-app
cd voicely-app
```

**Option B: Sử dụng Git (Nếu có private repository)**
```bash
# Trên server
git clone https://github.com/HudsonBui/Voicely-BE.git
cd Voicely-BE
git checkout implement_note_feature
```

### Bước 3: Chạy trên server

```bash
# 1. Copy file .env và chỉnh sửa
cp .env.example .env
nano .env  # Hoặc vim .env

# 2. Chạy Docker Compose
docker-compose up -d

# 3. Kiểm tra logs
docker-compose logs -f

# 4. Chạy migrations (nếu cần)
docker-compose exec app alembic upgrade head
```

### Bước 4: Cấu hình Nginx (Optional - cho production)

Tạo file `/etc/nginx/sites-available/voicely`:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Kích hoạt:
```bash
sudo ln -s /etc/nginx/sites-available/voicely /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Bước 5: Cài đặt SSL với Certbot (Optional)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 🏗️ **Cách 2: Build Docker Image và đẩy lên Registry**

### Bước 1: Build và push image

```bash
# 1. Build image
docker build -t voicely-backend:latest .

# 2. Tag cho Docker Hub (hoặc registry khác)
docker tag voicely-backend:latest your-dockerhub-username/voicely-backend:latest

# 3. Push lên registry
docker login
docker push your-dockerhub-username/voicely-backend:latest
```

### Bước 2: Trên server, pull và chạy

```bash
# 1. Pull image
docker pull your-dockerhub-username/voicely-backend:latest

# 2. Chạy database
docker run -d \
  --name voicely_db \
  -e POSTGRES_USER=voicely_user \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=voicely_db \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:15

# 3. Chạy app
docker run -d \
  --name voicely_app \
  -p 8000:8000 \
  -e DB_HOST=voicely_db \
  -e DB_NAME=voicely_db \
  -e DB_USER=voicely_user \
  -e DB_PASSWORD=your_password \
  -e JWT_SECRET_KEY=your_jwt_secret \
  -e JWT_REFRESH_SECRET_KEY=your_refresh_secret \
  -v $(pwd)/voicely-474001-842320946404.json:/code/voicely-474001-842320946404.json \
  --link voicely_db:db \
  your-dockerhub-username/voicely-backend:latest
```

---

## 🔧 **Cách 3: Triển khai trực tiếp (Không dùng Docker)**

### Bước 1: Cài đặt dependencies trên server

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Cài đặt Python 3.12
sudo apt install python3.12 python3.12-venv python3-pip -y

# 3. Cài đặt PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# 4. Cài đặt ffmpeg
sudo apt install ffmpeg -y
```

### Bước 2: Upload code và cấu hình

```bash
# 1. Upload code (như Cách 1)
# 2. Tạo virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 3. Cài đặt dependencies
pip install -r requirements.txt

# 4. Cấu hình PostgreSQL
sudo -u postgres psql
CREATE DATABASE voicely_db;
CREATE USER voicely_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE voicely_db TO voicely_user;
\q

# 5. Tạo file .env
cp .env.example .env
nano .env
```

### Bước 3: Chạy ứng dụng với systemd

Tạo file `/etc/systemd/system/voicely.service`:
```ini
[Unit]
Description=Voicely Backend API
After=network.target postgresql.service

[Service]
Type=notify
User=your-user
Group=your-user
WorkingDirectory=/home/your-user/voicely-app
Environment="PATH=/home/your-user/voicely-app/venv/bin"
EnvironmentFile=/home/your-user/voicely-app/.env
ExecStart=/home/your-user/voicely-app/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Kích hoạt service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable voicely
sudo systemctl start voicely
sudo systemctl status voicely
```

---

## 📊 Quản lý và Monitoring

### Xem logs
```bash
# Docker Compose
docker-compose logs -f app

# Docker container
docker logs -f voicely_app

# Systemd
sudo journalctl -u voicely -f
```

### Backup database
```bash
# Docker
docker-compose exec db pg_dump -U voicely_user voicely_db > backup.sql

# Trực tiếp
pg_dump -U voicely_user voicely_db > backup.sql
```

### Restore database
```bash
# Docker
cat backup.sql | docker-compose exec -T db psql -U voicely_user voicely_db

# Trực tiếp
psql -U voicely_user voicely_db < backup.sql
```

---

## 🔒 Security Checklist

- [ ] Đổi tất cả passwords mặc định
- [ ] Sử dụng JWT secrets mạnh (min 32 ký tự)
- [ ] Cấu hình firewall (chỉ mở port 80, 443, 22)
- [ ] Cài đặt SSL certificate
- [ ] Bảo vệ file credentials GCS
- [ ] Cấu hình CORS đúng trong FastAPI
- [ ] Sử dụng environment variables, không hardcode secrets
- [ ] Backup database định kỳ

---

## 🆘 Troubleshooting

### Port đã được sử dụng
```bash
# Kiểm tra process đang dùng port 8000
sudo lsof -i :8000
# Kill process
sudo kill -9 <PID>
```

### Database connection failed
```bash
# Kiểm tra PostgreSQL đang chạy
docker-compose ps  # Hoặc
sudo systemctl status postgresql
```

### Permission denied khi chạy Docker
```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## 📞 Support
Nếu gặp vấn đề, kiểm tra logs và Google Cloud Console để debug.

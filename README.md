Tài liệu này hướng dẫn chi tiết quy trình triển khai hệ thống PoseTracker (Computer Vision) từ môi trường Local lên server GPU High-Performance (NVIDIA H100) tại FPT AI Factory.


## Bước 1: Thiết lập môi trường trên GPU VM

Tạo SSH key và copy public key to FPT AI Factory (Chưa có thì hỏi AI cách generate SSH Key)
```bash
cat ~/.ssh/id_ed25519.pub
```

PUBLIC_IP lấy từ trong dashboard của FPT AI Factory
```bash
ssh ubuntu@[PUBLIC_IP]
```

Sau khi SSH vào server, thực hiện các bước sau:

### 1. Cập nhật hệ thống & Cài đặt thư viện Python
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv libgl1 -y
```

### 2. Clone Source Code
```bash
git clone https://github.com/Lloriozz/GDGoCPoseTracker.git
cd PoseTracker
```

### 3. Khởi tạo Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install daphne # Để chạy server ASGI
```

---

## Bước 2: Cấu hình Django 

Để server có thể nhận request từ bên ngoài (Internet) và mobile app, file `settings.py` cần được cấu hình chính xác để tránh lỗi `DisallowedHost` hoặc `ImproperlyConfigured`.

### 1. Cấu hình file `detect_model/web/server/exercise_correction/settings.py`
- **SECRET_KEY**: Đảm bảo không để trống.
- **ALLOWED_HOSTS**: Thêm IP của VM và dấu `*` để chấp nhận request từ Expo.
- **CORS**: Cấu hình `corsheaders` để tránh lỗi cross-origin trên mobile.

---

## Bước 3: Khởi chạy Server Backend

Sử dụng **Daphne** để hỗ trợ xử lý bất đồng bộ (Async), giúp việc nhận frame hình ảnh liên tục không bị nghẽn.

```bash
cd detect_model/web/server
source ../../.venv/bin/activate

# Chạy server ở chế độ công khai trên port 8000
daphne -b 0.0.0.0 -p 8000 exercise_correction.asgi:application
```
> **Lưu ý:** Đảm bảo Firewall của VM đã mở port 8000 


### Cập nhật code mới nhất từ GitHub:
```bash
git stash
git pull origin main
git stash pop
```

### Chạy ngầm server (Background process):
```bash
nohup daphne -b 0.0.0.0 -p 8000 exercise_correction.asgi:application > server.log 2>&1 &
```

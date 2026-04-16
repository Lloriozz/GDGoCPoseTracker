

### File README.md cho dự án của ông:

```markdown
# 🚀 PoseTracker AI Factory Deployment Guide

Tài liệu này hướng dẫn chi tiết quy trình triển khai hệ thống **PoseTracker** (Computer Vision) từ môi trường Local lên server GPU High-Performance (NVIDIA H100) tại FPT AI Factory.

---

## 📋 Tổng quan kiến trúc

- **Frontend:** React Native (Expo) - Chụp ảnh/Video frame và gửi qua API.
- **Backend:** Django (Daphne/ASGI) - Xử lý logic nghiệp vụ và quản lý session.
- **AI Engine:** MediaPipe / Unsupervised Models - Trích xuất 33 điểm landmarks của người dùng.
- **Infrastructure:** FPT AI Factory GPU VM (Ubuntu 22.04, NVIDIA H100).

---

## 🛠 Bước 1: Thiết lập môi trường trên GPU VM

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
git clone [https://github.com/Lloriozz/PoseTracker.git](https://github.com/Lloriozz/PoseTracker.git)
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

## ⚙️ Bước 2: Cấu hình Django (Cực kỳ quan trọng)

Để server có thể nhận request từ bên ngoài (Internet) và mobile app, file `settings.py` cần được cấu hình chính xác để tránh lỗi `DisallowedHost` hoặc `ImproperlyConfigured`.

### 1. Cấu hình file `detect_model/web/server/exercise_correction/settings.py`
- **SECRET_KEY**: Đảm bảo không để trống.
- **ALLOWED_HOSTS**: Thêm IP của VM và dấu `*` để chấp nhận request từ Expo.
- **CORS**: Cấu hình `corsheaders` để tránh lỗi cross-origin trên mobile.

### 2. Lệnh fix nhanh bằng Terminal
```bash
# Thêm SECRET_KEY và ALLOWED_HOSTS chuẩn
cat << 'EOF' > detect_model/web/server/exercise_correction/settings.py
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-long-nguyen-dinh-pose-tracker-2026'
DEBUG = True
ALLOWED_HOSTS = ['*']

# ... (Giữ nguyên các cấu hình INSTALLED_APPS và MIDDLEWARE hiện có)
EOF
```

---

## 🚀 Bước 3: Khởi chạy Server Backend

Sử dụng **Daphne** để hỗ trợ xử lý bất đồng bộ (Async), giúp việc nhận frame hình ảnh liên tục không bị nghẽn.

```bash
cd detect_model/web/server
source ../../.venv/bin/activate

# Chạy server ở chế độ công khai trên port 8000
daphne -b 0.0.0.0 -p 8000 exercise_correction.asgi:application
```
> **Lưu ý:** Đảm bảo Firewall của VM đã mở port 8000 (Inbound).

---

## 📱 Bước 4: Tối ưu hóa Mobile App (Frontend)

Để đạt trải nghiệm Real-time, Frontend (React Native) cần được tinh chỉnh để giảm độ trễ (Latency):

1. **Tối ưu Frame Capture:**
   - Giảm `quality` ảnh xuống mức `0.15` - `0.2`.
   - Sử dụng `skipProcessing: true` để lấy ảnh nhanh nhất.
   - Đặt `CAPTURE_INTERVAL_MS` khoảng `150ms` - `200ms`.

2. **Xử lý hiển thị (Smooth Tracking):**
   - Sử dụng `Animated.ValueXY` để nội suy vị trí các điểm landmarks, tránh tình trạng giật (stuttering).
   - Mapping tọa độ chuẩn: `x: (1 - point.x) * SCREEN_W` (dành cho camera trước).

---

## 🔍 Bước 5: Kiểm tra kết quả

Khi hệ thống hoạt động chính xác, log trên server sẽ nhảy liên tục với mã trạng thái `200 OK`:
```text
171.246.x.x - - [14/Apr/2026:16:59:45] "POST /api/pose/analyze/..." 200 3615
```

### Các lỗi thường gặp và cách xử lý:

| Lỗi | Nguyên nhân | Cách sửa |
| :--- | :--- | :--- |
| **IndentationError** | Sai định dạng thụt đầu dòng Python | Kiểm tra lại file settings.py bằng lệnh `cat -A` |
| **DisallowedHost** | IP server chưa nằm trong ALLOWED_HOSTS | Thêm `'*'` vào list ALLOWED_HOSTS |
| **Bad Request (400)** | Header Host không khớp | Đảm bảo app gửi request đúng IP public của VM |
| **Points not matching** | Sai tỉ lệ màn hình/Mirroring | Chỉnh lại logic `(1 - x)` trong hàm `getPoint` |

---

## 🛠 Maintenance (Bảo trì)

### Cập nhật code mới nhất từ GitHub:
```bash
git stash
git pull origin feature/cardio
git stash pop
```

### Chạy ngầm server (Background process):
```bash
nohup daphne -b 0.0.0.0 -p 8000 exercise_correction.asgi:application > server.log 2>&1 &
```

---
**Author:** Nguyễn Đình Long & Team ByTe - S  
**Project:** PoseTracker AI Factory Deployment 2026
```

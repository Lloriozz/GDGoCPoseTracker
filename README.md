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


# Quy trình triển khai Chatbot Backend trên GPU VM

Tài liệu này mô tả quy trình thiết lập và khởi chạy hệ thống chatbot backend trên máy chủ GPU VM. Hệ thống backend được triển khai từ repository `GDGoCPoseTracker`, trong đó phần chatbot nằm trong thư mục `backend` của nhánh `main`, còn các tệp mô hình ngôn ngữ lớn (LLM) được tổ chức trong thư mục `backend/modelLLM`.

## Bước 1: Thiết lập môi trường trên GPU VM

Trước khi triển khai, cần chuẩn bị quyền truy cập SSH vào máy ảo GPU được cấp trên nền tảng FPT AI Factory.

### 1. Tạo SSH key và lấy public key

Nếu chưa có SSH key, cần tạo mới và sao chép public key để cấu hình quyền truy cập trên FPT AI Factory.

```bash
cat ~/.ssh/id_ed25519.pub
```
2. Kết nối tới GPU VM

Địa chỉ PUBLIC_IP được cung cấp trong dashboard của FPT AI Factory.
```bash
ssh ubuntu@[PUBLIC_IP]
```
Sau khi đăng nhập thành công, chuyển sang quyền quản trị:
```bash
sudo -i
```
Bước 2: Tải mã nguồn từ GitHub

Clone repository từ GitHub:
```bash
git clone https://github.com/Lloriozz/GDGoCPoseTracker.git
cd ~/GDGoCPoseTracker
```
Do phần chatbot backend nằm trong nhánh main, không cần checkout sang nhánh khác nếu mục tiêu là triển khai backend hiện tại.

Có thể kiểm tra các nhánh hiện có bằng lệnh:
```bash
git branch -a
```
Sau đó chuyển vào thư mục backend:
```bash
cd backend
```
Lưu ý: Thư mục backend là nơi chứa mã nguồn backend chatbot. Các tệp liên quan tới mô hình LLM được đặt trong thư mục backend/modelLLM theo cấu trúc triển khai hiện tại của dự án.

Bước 3: Cài đặt môi trường Python

Trước tiên, cập nhật danh sách gói hệ thống:
```bash
apt update
```
Cài đặt Python 3.11, công cụ tạo môi trường ảo và các thành phần cần thiết:
```bash
apt install -y python3.11 python3.11-venv python3-pip git
```
Khởi tạo virtual environment ngay trong thư mục backend:
```bash
python3.11 -m venv .venv
```
Kích hoạt môi trường ảo:
```bash
source .venv/bin/activate
```
Nâng cấp pip:
```bash
python -m pip install --upgrade pip
```
Bước 4: Cài đặt các thư viện phụ thuộc

Cài đặt các thư viện backend và thành phần phục vụ suy luận mô hình:
```bash
pip install fastapi "uvicorn[standard]" pydantic accelerate sentencepiece protobuf huggingface_hub
```
Cài đặt PyTorch tương thích CUDA 12.4:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```
Cài đặt thư viện transformers phiên bản mới nhất từ GitHub:
```bash
pip install git+https://github.com/huggingface/transformers
```
Để đảm bảo môi trường đã được kích hoạt chính xác, có thể chạy lại:
```bash
source .venv/bin/activate
```
Bước 5: Vị trí lưu trữ mô hình LLM

Trong cấu trúc backend hiện tại, các tệp mô hình ngôn ngữ lớn được đặt trong thư mục:

backend/modelLLM

Thư mục này được sử dụng để lưu trữ hoặc quản lý các model files phục vụ backend chatbot trong quá trình triển khai nội bộ.

Tùy theo cách tổ chức runtime, backend có thể:

tải mô hình trực tiếp từ Hugging Face thông qua GEMMA_MODEL_ID, hoặc
sử dụng các tệp mô hình đã được đặt sẵn trong backend/modelLLM để phục vụ suy luận cục bộ.

Với trường hợp triển khai thực tế trên GPU VM, cần bảo đảm các model files cần thiết đã được đặt đúng trong thư mục này nếu hệ thống yêu cầu chạy từ tệp cục bộ.

Bước 6: Cấu hình biến môi trường

Trước khi khởi chạy backend, cần cấu hình các biến môi trường liên quan tới cơ sở dữ liệu và backend mô hình ngôn ngữ.

1. Cấu hình kết nối cơ sở dữ liệu PostgreSQL
```bash
export DATABASE_URL='[POSTGRESQL_DATABASE_URL]'
export DATABASE_SCHEMA=public
```
2. Cấu hình backend mô hình ngôn ngữ

Thiết lập như sau:
```bash
export LLM_BACKEND=gemma_local
export GEMMA_MODEL_ID=./modelLLM
export GEMMA_DEVICE=cuda
export GEMMA_DTYPE=bfloat16
export GEMMA_QUANTIZATION=none
export GEMMA_CPU_OFFLOAD=false
export GEMMA_OFFLOAD_BUFFERS=false
export GEMMA_GPU_MEMORY_LIMIT_MB=0
export GEMMA_CPU_MEMORY_LIMIT_MB=0
```

Bước 7: Khởi chạy backend server

# Chạy server ở chế độ công khai trên port 8000
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
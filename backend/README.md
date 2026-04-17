# PoseTracker Backend

Node.js backend for PoseTracker application with PostgreSQL + pgvector.

## Tech Stack
- **Node.js** + **TypeScript**
- **Express.js** (Web Framework)
- **Prisma** (ORM)
- **PostgreSQL** + **pgvector** (Database)
- **Cloudinary** (Media Storage)
- **JWT** (Authentication)

## Getting Started

### Prerequisites
- Node.js 18+ 
- PostgreSQL 14+ with pgvector extension
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Update .env with your database credentials
```

### Database Setup

```bash
# Generate Prisma client
npm run prisma:generate

# Run migrations
npm run prisma:migrate

# Open Prisma Studio (optional)
npm run prisma:studio
```

### Development

```bash
# Start development server
npm run dev
```

### Production

```bash
# Build the project
npm run build

# Start production server
npm start
```

## API Endpoints

- `GET /health` - Health check endpoint

## Environment Variables

See `.env.example` for required environment variables.

# Fitness Chatbot Skeleton

Skeleton `FastAPI + orchestrator + schema` cho chatbot fitness tiếng Việt.

## Chạy local

```bash
uvicorn app.main:app --reload
```

Luu y:

- Hay chay lenh nay tu thu muc goc cua project: `C:\Users\Huy\OneDrive\Documents\New project`
- Neu ban `cd app` roi moi chay `uvicorn app.main:app --reload` thi se bi loi `ModuleNotFoundError: No module named 'app'`

## Endpoint chính

`POST /chat`

Ví dụ request:

```json
{
  "user_id": "user-001",
  "session_id": "session-001",
  "message": "Tính TDEE cho tôi",
  "profile_patch": {
    "age": 24,
    "sex": "male",
    "height_cm": 175,
    "weight_kg": 72,
    "activity_level": "moderate",
    "goal": "muscle_gain"
  }
}
```

## Luồng hiện tại

- `routes/chat.py`: nhận request
- `core/orchestrator.py`: điều phối intent, slot filling, safety, tool call
- `memory/`: lưu profile và chat history trong RAM
- `db/database.py`: khoi tao SQLite va tao bang memory
- `tools/tdee.py`: tool tính TDEE mẫu
- `llm/mock_gemma.py`: mock Gemma de giu app chay on dinh
- `llm/gemma_local.py`: local backend skeleton cho Gemma that
- `llm/factory.py`: chon backend theo config

## Bước tiếp theo nên làm

- Mo rong memory SQLite thanh session store day du
- Thêm workout tool, macro tool, meal plan tool
- Thêm prompt template rõ hơn
- Nối Gemma thật qua Transformers hoặc inference server
- Thêm test và logging

## LLM backend config

- `LLM_BACKEND=mock-gemma`: giu hanh vi mock hien tai
- `LLM_BACKEND=local-transformers`: chuyen sang local Gemma skeleton
- `GEMMA_MODEL_ID`: id model Gemma muon dung
- `GEMMA_DEVICE`: `cuda`, `cpu`, ...
- `GEMMA_DTYPE`: `bfloat16`, `float16`, ...
- `GEMMA_QUANTIZATION`: `4bit`, `8bit`, `none`
- `GEMMA_TOP_P`: top-p sampling cho local backend
- `GEMMA_DO_SAMPLE`: bat sampling hay chay deterministic
- `GEMMA_TRUST_REMOTE_CODE`: bat khi model/backend can
- `GEMMA_CPU_OFFLOAD`: cho phep offload mot phan model sang CPU
- `GEMMA_OFFLOAD_BUFFERS`: bat offload buffer neu VRAM rat chat
- `GEMMA_GPU_MEMORY_LIMIT_MB`: gioi han VRAM ma `device_map=auto` duoc phep dung
- `GEMMA_CPU_MEMORY_LIMIT_MB`: gioi han RAM cho phan offload

## Local Gemma notes

- Model id mac dinh da dat theo Hugging Face model card: `google/gemma-4-E4B-it`
- De dung local backend, can cai them dependency `transformers`, `accelerate`, `sentencepiece`, va `torch`
- Neu dung quantization `4bit/8bit`, can them `bitsandbytes`
- Tren may RTX 2050 4GB, `4bit` la cach thu hop ly nhat, nhung van co kha nang gap OOM vi Gemma 4 E4B-it khong nhe

## Test local backend

1. Chay local backend:

```powershell
.\run_local_backend.ps1
```

2. Mo terminal thu hai va goi test API:

```powershell
.\test.ps1
```

3. Neu muon doi mode:

```powershell
.\run_local_backend.ps1 -Device cuda -Quantization 4bit -CpuOffload $true -OffloadBuffers $true
```

Script se uu tien dung model local tai `D:\hackathon\chatbot\models\gemma-4-E4B-it` neu thu muc do ton tai. Neu khong, no moi fallback ve Hugging Face model id.

Neu GPU khong du bo nho, hay thu lai bang CPU de smoke test wiring:

```powershell
.\run_local_backend.ps1 -Device cpu -Quantization none -DType float32
```

Voi GPU 4GB, nen uu tien:

```powershell
.\run_local_backend.ps1 -Device cuda -Quantization 4bit -GpuMemoryLimitMB 3000 -CpuMemoryLimitMB 24576
```

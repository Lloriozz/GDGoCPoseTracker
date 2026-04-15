# PoseTracker Frontend

Frontend mobile-first cho flow `Home -> PT button -> ChatBot`, dựng bằng Expo Router trong:

`C:\Users\Huy\OneDrive\Documents\New project\frontend`

## Chạy local

```bash
npm install
npx expo start
```

## Nối backend FastAPI

1. Chạy backend Python ở cổng `8000`
2. Tạo file `.env` từ `.env.example`
3. Nếu test trên máy thật, đổi `EXPO_PUBLIC_API_HOST` thành IP LAN của máy chạy backend

## Flow hiện có

- Home screen bám theo mockup PoseTracker
- Nút `PT` nổi ở góc dưới phải mở screen chatbot
- Chatbot gọi `POST /chat` của backend FastAPI hiện tại

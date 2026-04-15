# Backend Deployment

This backend is ready to deploy as a Docker web service.

## Render

1. Push the repo to GitHub.
2. In Render, create a new Web Service.
3. Connect the repository.
4. Set the Root Directory to `detect_model`.
5. Choose Docker as the runtime.
6. Add the environment variables from `.env.example`.
7. Deploy and wait for the public URL.

Recommended values:

- `DJANGO_DEBUG=false`
- `DJANGO_SECRET_KEY=<long random string>`
- `DJANGO_ALLOWED_HOSTS=<your-render-hostname>`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-render-hostname>`
- `DJANGO_CORS_ALLOWED_ORIGINS=https://expo.dev`

## Railway

1. Create a new project from the GitHub repository.
2. Point the service root to `detect_model`.
3. Use the included `Dockerfile`.
4. Add the same environment variables as Render.
5. Deploy and copy the public domain Railway gives you.

## Local smoke test

Build the container:

```bash
docker build -t posetracker-backend ./detect_model
```

Run it:

```bash
docker run --rm -p 8000:8000 \
  -e DJANGO_DEBUG=true \
  -e DJANGO_SECRET_KEY=dev-secret \
  -e DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost \
  posetracker-backend
```

Then open:

- `http://127.0.0.1:8000/api/`
- `http://127.0.0.1:8000/api/pose/analyze/?type=squat`

The second endpoint expects a POST request with JSON body:

```json
{
  "frame": "<base64 image payload>"
}
```

## Expo setup

Once the backend is deployed, set this in `frontend/.env`:

```env
EXPO_PUBLIC_POSE_API_BASE_URL=https://your-backend-domain.com
```

Then run:

```bash
cd frontend
npx expo start --tunnel
```

Users can scan the QR code and the mobile app will call the online backend.

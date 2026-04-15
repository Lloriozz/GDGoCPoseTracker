# Local Backend Setup

This guide explains how to run the PoseTracker backend on your Mac and test the Expo mobile app on your phone before deploying to Render.

## What You Are Running

- `frontend/` = Expo mobile app
- `detect_model/web/server/` = Django backend API for pose detection

The phone does not run the `.pkl` models directly.  
Your phone sends frames to the Django backend running on your Mac.

## 1. Install Python Dependencies

From the repo root:

```bash
cd /Users/dinhlong/Documents/GitHub/PoseTracker/detect_model
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If `requirements.txt` gives you trouble on your Mac, try:

```bash
pip install -r requirements-mac.txt
```

## 2. Start the Backend Locally

Run:

```bash
cd /Users/dinhlong/Documents/GitHub/PoseTracker/detect_model/web/server
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Important:
- `0.0.0.0:8000` is required so your phone can reach your Mac
- keep this terminal running while testing

## 3. Find Your Mac Local IP

Run this on your Mac:

```bash
ipconfig getifaddr en0
```

If that returns nothing, try:

```bash
ipconfig getifaddr en1
```

Example result:

```text
192.168.1.15
```

Your local backend URL will then be:

```text
http://192.168.1.15:8000
```

## 4. Confirm the Backend Is Reachable

On your Mac browser, open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/api/`

Then on your phone browser, open:

- `http://YOUR_LOCAL_IP:8000/api/`

Example:

- `http://192.168.1.15:8000/api/`

If your phone cannot open that URL:
- make sure the phone and Mac are on the same Wi-Fi
- make sure macOS firewall is not blocking Python
- make sure the Django server is running on `0.0.0.0:8000`

## 5. Point Expo to Your Local Backend

Edit:

[`frontend/.env`](/Users/dinhlong/Documents/GitHub/PoseTracker/frontend/.env)

Set:

```env
EXPO_PUBLIC_POSE_API_BASE_URL=http://YOUR_LOCAL_IP:8000
```

Example:

```env
EXPO_PUBLIC_POSE_API_BASE_URL=http://192.168.1.15:8000
```

Important:
- use your Mac LAN IP
- do not use `localhost`
- do not use `127.0.0.1`

Because from the phone, `localhost` means the phone itself, not your Mac.

## 6. Start the Expo App

In a new terminal:

```bash
cd /Users/dinhlong/Documents/GitHub/PoseTracker/frontend
npx expo start --clear --lan
```

Then:
- open Expo Go on your phone
- scan the QR code

Important:
- your phone and Mac must stay on the same Wi-Fi
- if Expo Go keeps showing an old bundle, fully close Expo Go and scan again

## 7. Test Pose Tracking

In the app:

1. Open the pose tracker
2. Choose an exercise
3. Allow camera access
4. Stand where the full required body area is visible

Expected behavior:
- if the pose is not visible: you should see a framing message
- if landmarks are detected: you should see dots, score, and correction text

## 8. Common Local Problems

### Problem: The phone app says it cannot reach the backend

Check:
- backend terminal is still running
- `frontend/.env` uses `http://YOUR_LOCAL_IP:8000`
- phone can open `http://YOUR_LOCAL_IP:8000/api/` in Safari/Chrome

### Problem: It still shows the old deployed URL

Restart Expo fully:

```bash
cd /Users/dinhlong/Documents/GitHub/PoseTracker/frontend
npx expo start --clear --lan
```

Then close Expo Go and rescan the QR.

### Problem: It detects nothing

Try:
- better lighting
- move farther from the camera
- keep the full body in frame for squat/lunge/plank
- keep shoulder, elbow, wrist visible for bicep curl

### Problem: macOS asks about firewall/network

Allow Python or the terminal app to accept incoming connections.

## 9. When You Are Ready to Deploy

After local testing works:

1. Deploy the backend to Render
2. Change `frontend/.env` to:

```env
EXPO_PUBLIC_POSE_API_BASE_URL=https://posetracker.onrender.com
```

3. Restart Expo:

```bash
npx expo start --clear --lan
```

Or use tunnel if needed.

## Quick Start Summary

Backend:

```bash
cd /Users/dinhlong/Documents/GitHub/PoseTracker/detect_model
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd web/server
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Frontend:

```bash
cd /Users/dinhlong/Documents/GitHub/PoseTracker/frontend
npx expo start --clear --lan
```

Frontend `.env`:

```env
EXPO_PUBLIC_POSE_API_BASE_URL=http://YOUR_LOCAL_IP:8000
```

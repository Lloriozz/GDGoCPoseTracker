This document provides a detailed guide on deploying the PoseTracker (Computer Vision) system from a Local environment to a High-Performance GPU server (NVIDIA H100) at FPT AI Factory.

## Step 1: Setting up the Environment on the GPU VM

Generate an SSH key and copy the public key to FPT AI Factory (If you don't have one, ask the AI how to generate an SSH Key).
```bash
cat ~/.ssh/id_ed25519.pub
```

Obtain the PUBLIC_IP from the FPT AI Factory dashboard.
```bash
ssh ubuntu@[PUBLIC_IP]
```

After establishing an SSH connection to the server, perform the following steps:

### 1. Update the System & Install Python Libraries
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv libgl1 -y
```

### 2. Clone the Source Code
```bash
git clone https://github.com/Lloriozz/GDGoCPoseTracker.git
cd PoseTracker
```

### 3. Initialize the Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install daphne # To run the ASGI server
```

---

## Step 2: Django Configuration

To allow the server to accept requests from the outside (Internet) and the mobile app, the `settings.py` file must be configured correctly to avoid `DisallowedHost` or `ImproperlyConfigured` errors.

### 1. Configure the `detect_model/web/server/exercise_correction/settings.py` file
- **SECRET_KEY**: Ensure this is not empty.
- **ALLOWED_HOSTS**: Add the VM's IP address and a wildcard `*` to accept requests from Expo.
- **CORS**: Configure `corsheaders` to prevent cross-origin errors on the mobile app.

---

## Step 3: Run the Backend Server

Use **Daphne** to support asynchronous (Async) processing, ensuring that continuous image frame reception is not bottlenecked.

```bash
cd detect_model/web/server
source ../../.venv/bin/activate

# Run the server publicly on port 8000
daphne -b 0.0.0.0 -p 8000 exercise_correction.asgi:application
```
> **Note:** Ensure that the VM's Firewall has port 8000 open.


### Pull the latest code from GitHub:
```bash
git stash
git pull origin main
git stash pop
```

### Run the server in the background:
```bash
nohup daphne -b 0.0.0.0 -p 8000 exercise_correction.asgi:application > server.log 2>&1 &
```
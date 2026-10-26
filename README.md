#  Lulu Enterprise Digital Adoption Platform (DAP)

A full-stack, cloud-connected interactive desktop onboarding assistant and enterprise behavioral telemetry tracker.

Lulu acts as a dynamic, floating UI overlay that guides new employees through complex enterprise desktop software (such as billing and CRM portals) using physics-based neon indicators, step-by-step guidance, and Microsoft Edge-TTS neural voice narration. Managers can track live employee progress, detect bottlenecks, and update workflows in real-time via a modern command center dashboard backed by **MongoDB Atlas** and **WebSockets**.

---

##  System Architecture

The project consists of three core components communicating over HTTP and WebSockets:

1. **Lulu Backend API & Command Center (`lulu-backend-api/server.py`)**
   - Built with **FastAPI**, **WebSockets**, and **PyJWT**.
   - **Real-Time Bidirectional Sync**: Instant telemetry streaming to connected manager dashboards and zero-restart workflow updates broadcasted to desktop clients.
   - **Multi-Workflow Engine**: Stores multiple workflows across departments (Billing, CRM, Warehouse) with dynamic activation.
   - **Security**: JWT-based Manager Authentication guard (`/api/auth/login`) protecting workflow mutations.
   - **Environment Configuration**: Secrets and MongoDB URIs managed via `.env`.
   - **MongoDB Atlas Cloud**: Resilient TLS bypass configuration (`tlsAllowInvalidCertificates=True`) ensuring uninterrupted database connectivity across strict ISP firewalls.

2. **Lulu Desktop HUD Client (`lulu-desktop-client/lulu_main.py`)**
   - Built with **PyQt6** and **QtWebSockets**.
   - **Transparent Full-Screen HUD**: Physics-based lerp pointer, breathing neon bloom, expanding sonar ripple rings, and glassmorphic pill badge.
   - **Context-Aware Auto-Detection**: Dynamically scans running desktop windows (`pywinauto` UIA backend). Automatically switches workflows when the trainee switches between different enterprise apps!
   - **Zero-Restart Live Sync**: Listens on `ws://127.0.0.1:5000/ws/client`. When a manager edits or switches a workflow in the dashboard, Lulu updates on screen immediately.
   - **Edge-TTS Neural Audio**: Asynchronous voice narration using `edge-tts` and `pygame.mixer`.

3. **Enterprise Demonstration Targets (`demo-billing-app/`)**
   - **Billing Portal** (`demo-billing-app/billing_software.py`): Demonstrates the Customer Refund workflow.
   - **CRM Portal** (`demo-billing-app/crm_software.py`): Demonstrates the Customer Account Setup workflow and multi-app switching.

---

##  Key Enterprise Features

*  **Zero-Delay WebSocket Sync:** Step completions flash instantly on the manager dashboard; workflow updates deploy to trainee screens in real-time without app restarts.
*  **Multi-Workflow & Multi-App Support:** Manage guides for different desktop portals (Billing, CRM, Inventory). Lulu auto-detects which application window is focused.
*  **Manager JWT Authentication:** Secure login session (`admin` / `luluadmin123`) protecting workflow deployment and telemetry resetting.
*  **Live Bottleneck Analytics:** Animated Chart.js dashboard color-coding step durations (pink indicators for steps taking ≥ 8.0s).
*  **Neural Voice Narration:** Edge-TTS speech engine gives clear spoken instructions at every step.
*  **Network-Resilient Cloud Architecture:** MongoDB Atlas connection with SSL bypass to prevent Windows ISP connection drops (`TLSV1_ALERT_INTERNAL_ERROR`).

---

##  Prerequisites & Installation

### 1. Requirements
* **Python 3.10+** (Tested on Python 3.11)
* Active internet connection for MongoDB Atlas cloud sync & Edge-TTS

### 2. Install Dependencies
```powershell
pip install fastapi uvicorn pymongo certifi dnspython pygame pywinauto edge-tts requests python-dotenv pyjwt websockets PyQt6
```

### 3. Environment Configuration
Verify your `lulu-backend-api/.env` file:
```ini
SERVER_HOST=127.0.0.1
SERVER_PORT=5000
MONGO_URI=mongodb+srv://aselmarsh06_db_user:22wZsQI9JGC629Xk@cluster0.pc1tiy6.mongodb.net/?retryWrites=true&w=majority
DB_NAME=lulu_enterprise_db
JWT_SECRET=lulu_enterprise_super_secret_jwt_key_2026_capstone_secure!
MANAGER_USERNAME=admin
MANAGER_PASSWORD=luluadmin123
```

---

##  Running the System

### Step 1: Start the Backend Server
```powershell
cd Lulu-Onboarding-System
python lulu-backend-api\server.py
```
*Manager Command Center is accessible at `http://127.0.0.1:5000`.*
*Default credentials: Username: `admin` | Password: `luluadmin123`.*

### Step 2: Run Automated Integration Tests (Optional)
Run the automated test suite to verify all 7 WebSocket, JWT, and multi-workflow endpoints:
```powershell
python test_enterprise_sync.py
```

### Step 3: Launch Enterprise Apps and Lulu Desktop HUD
Open a new PowerShell terminal and start the target app and Lulu overlay:
```powershell
cd Lulu-Onboarding-System

# Launch Billing Portal Demo and Lulu HUD:
Start-Process python -ArgumentList "demo-billing-app\billing_software.py"; python lulu-desktop-client\lulu_main.py
```

To demonstrate **multi-app auto-detection**, also launch the CRM Portal:
```powershell
python demo-billing-app\crm_software.py
```
*Watch Lulu seamlessly detect the open portal and switch workflows automatically!*

---

##  Troubleshooting

* **Manager Dashboard Login:**
  Click **Manager Login** on `http://127.0.0.1:5000` and use `admin` / `luluadmin123`.
* **QuickEdit Freeze in Terminal:**
  If you click inside the PowerShell terminal window running `server.py`, Windows may pause the process. Press `Enter` in that terminal to unfreeze.
* **SSL / TLSV1_ALERT_INTERNAL_ERROR:**
  The `server.py` connection enforces `tls=True` and `tlsAllowInvalidCertificates=True` to bypass local ISP certificate firewalls. Ensure `certifi` is installed.
* **WebSocket Indicator Disconnected:**
  Ensure `server.py` is running on port 5000. The dashboard and HUD client will automatically attempt to reconnect every 2.5–3 seconds.

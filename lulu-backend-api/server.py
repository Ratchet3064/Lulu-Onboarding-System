import os
import sys
import json
import pathlib
from datetime import datetime, timedelta
from typing import List, Set, Optional

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from dotenv import load_dotenv
import jwt
from fastapi import (
    FastAPI, Request, WebSocket, WebSocketDisconnect,
    HTTPException, Depends, status
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pymongo import MongoClient

# ==========================================================
# LOAD ENVIRONMENT & SECRETS
# ==========================================================
BASE_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "5000"))

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI not configured. Please define MONGO_URI in your .env file.")
DB_NAME = os.getenv("DB_NAME", "lulu_enterprise_db")

JWT_SECRET = os.getenv("JWT_SECRET", "lulu_enterprise_default_secret_key_change_me_2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

MANAGER_USERNAME = os.getenv("MANAGER_USERNAME", "admin")
MANAGER_PASSWORD = os.getenv("MANAGER_PASSWORD", "luluadmin123")

# ==========================================================
# MONGODB ATLAS CLOUD CONNECTION (With SSL Bypass)
# ==========================================================
# Resilient SSL bypass to prevent Windows ISP firewall / certificate errors
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client[DB_NAME]

workflow_collection = db["workflows"]
telemetry_collection = db["telemetry"]

# ==========================================================
# DEFAULT MULTI-WORKFLOW SEED DATA
# ==========================================================
DEFAULT_WORKFLOWS = [
    {
        "workflow_id": "wf_refund_01",
        "title": "Customer Refund Onboarding Guide",
        "window_title": "Enterprise Billing Portal",
        "category": "Billing & Finance",
        "is_active": True,
        "steps": [
            {
                "step_num": 1,
                "target_button": "Open Customer Invoices",
                "badge_text": "Step 1: Click 'Open Customer Invoices'",
                "voice_text": "Welcome! Step 1: Click Open Customer Invoices.",
                "verify_screen_text": "Open Customer Invoices (Done)"
            },
            {
                "step_num": 2,
                "target_button": "Verify Account Balance",
                "badge_text": "Step 2: Click 'Verify Account Balance'",
                "voice_text": "Great! Step 2: Click Verify Account Balance.",
                "verify_screen_text": "Verify Account Balance (Done)"
            },
            {
                "step_num": 3,
                "target_button": "Approve & Issue Refund",
                "badge_text": "Step 3: Click 'Approve & Issue Refund'",
                "voice_text": "Almost done! Step 3: Click Approve and Issue Refund.",
                "verify_screen_text": "Approve & Issue Refund (Done)"
            }
        ]
    },
    {
        "workflow_id": "wf_crm_02",
        "title": "CRM Customer Account Setup",
        "window_title": "Enterprise CRM Portal",
        "category": "Customer Relations",
        "is_active": False,
        "steps": [
            {
                "step_num": 1,
                "target_button": "Create Customer Record",
                "badge_text": "Step 1: Click 'Create Customer Record'",
                "voice_text": "Welcome to CRM onboarding. Step 1: Click Create Customer Record.",
                "verify_screen_text": "Create Customer Record (Done)"
            },
            {
                "step_num": 2,
                "target_button": "Configure Credit Limit",
                "badge_text": "Step 2: Click 'Configure Credit Limit'",
                "voice_text": "Step 2: Set the credit terms and verify KYC profile.",
                "verify_screen_text": "Configure Credit Limit (Done)"
            },
            {
                "step_num": 3,
                "target_button": "Dispatch Onboarding Welcome",
                "badge_text": "Step 3: Click 'Dispatch Onboarding Welcome'",
                "voice_text": "Step 3: Send the official welcome packet to finalize setup.",
                "verify_screen_text": "Dispatch Onboarding Welcome (Done)"
            }
        ]
    },
    {
        "workflow_id": "wf_inventory_03",
        "title": "Warehouse Stock Audit Guide",
        "window_title": "Enterprise Inventory Portal",
        "category": "Logistics & Supply Chain",
        "is_active": False,
        "steps": [
            {
                "step_num": 1,
                "target_button": "Scan Bin Barcode",
                "badge_text": "Step 1: Click 'Scan Bin Barcode'",
                "voice_text": "Step 1: Scan the storage bin barcode to initiate the inventory count.",
                "verify_screen_text": "Scan Bin Barcode (Done)"
            },
            {
                "step_num": 2,
                "target_button": "Reconcile Cycle Count",
                "badge_text": "Step 2: Click 'Reconcile Cycle Count'",
                "voice_text": "Step 2: Compare physically counted goods with ERP numbers.",
                "verify_screen_text": "Reconcile Cycle Count (Done)"
            },
            {
                "step_num": 3,
                "target_button": "Post Audit Ledger",
                "badge_text": "Step 3: Click 'Post Audit Ledger'",
                "voice_text": "Step 3: Post the ledger adjustment to commit audit changes.",
                "verify_screen_text": "Post Audit Ledger (Done)"
            }
        ]
    }
]

# Ensure database is seeded with multi-workflows
if workflow_collection.count_documents({}) == 0:
    workflow_collection.insert_many(DEFAULT_WORKFLOWS)
else:
    # Ensure legacy database entries have workflow_id and is_active
    active_exists = workflow_collection.find_one({"is_active": True})
    if not active_exists:
        first_doc = workflow_collection.find_one({})
        if first_doc:
            workflow_collection.update_one({"_id": first_doc["_id"]}, {"$set": {"is_active": True}})

# ==========================================
# REAL-TIME WEBSOCKET CONNECTION MANAGER
# ==========================================
class WebSocketManager:
    def __init__(self):
        self.dashboard_sockets: Set[WebSocket] = set()
        self.client_sockets: Set[WebSocket] = set()

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_sockets.add(websocket)
        # Immediately notify dashboard of connected desktop clients count
        await self.broadcast_client_count()

    def disconnect_dashboard(self, websocket: WebSocket):
        self.dashboard_sockets.discard(websocket)

    async def connect_client(self, websocket: WebSocket):
        await websocket.accept()
        self.client_sockets.add(websocket)
        await self.broadcast_client_count()

    async def disconnect_client(self, websocket: WebSocket):
        self.client_sockets.discard(websocket)
        await self.broadcast_client_count()

    async def broadcast_client_count(self):
        payload = {
            "type": "CLIENT_COUNT_UPDATE",
            "count": len(self.client_sockets)
        }
        await self.broadcast_to_dashboards(payload)

    async def broadcast_to_dashboards(self, data: dict):
        message = json.dumps(data)
        disconnected = set()
        for ws in self.dashboard_sockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            self.dashboard_sockets.discard(ws)

    async def broadcast_to_clients(self, data: dict):
        message = json.dumps(data)
        disconnected = set()
        for ws in self.client_sockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            self.client_sockets.discard(ws)


ws_manager = WebSocketManager()

# ==========================================
# SECURITY & AUTHENTICATION
# ==========================================
security_bearer = HTTPBearer(auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def require_manager_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)):
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing manager authorization token"
        )
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Manager token has expired")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


# ==========================================
# FASTAPI APP CONFIGURATION
# ==========================================
app = FastAPI(
    title="Lulu Enterprise Onboarding & Telemetry API",
    description="Full-stack real-time DAP server with WebSocket synchronization and multi-workflow intelligence.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# MANAGER AUTHENTICATION ENDPOINTS
# ==========================================
@app.post("/api/auth/login")
async def manager_login(request: Request):
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()

    if username == MANAGER_USERNAME and password == MANAGER_PASSWORD:
        token = create_access_token(data={"sub": username, "role": "manager"})
        return {
            "status": "success",
            "access_token": token,
            "token_type": "bearer",
            "username": username,
            "expires_in_hours": JWT_EXPIRATION_HOURS
        }
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid manager credentials")

@app.get("/api/auth/me")
async def get_current_manager(username: str = Depends(require_manager_auth)):
    return {"status": "authenticated", "username": username, "role": "manager"}


# ==========================================
# MULTI-WORKFLOW API ENDPOINTS
# ==========================================
@app.get("/api/workflows")
def list_workflows():
    workflows = list(workflow_collection.find({}, {"_id": 0}))
    return workflows

@app.get("/api/workflow/active")
def get_active_workflow():
    wf = workflow_collection.find_one({"is_active": True}, {"_id": 0})
    if not wf:
        wf = workflow_collection.find_one({}, {"_id": 0})
    return wf or DEFAULT_WORKFLOWS[0]

@app.get("/api/workflow/{workflow_id}")
def get_workflow_by_id(workflow_id: str):
    wf = workflow_collection.find_one({"workflow_id": workflow_id}, {"_id": 0})
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf

# Backward compatibility endpoint for desktop client
@app.get("/api/workflow")
def get_default_workflow():
    return get_active_workflow()

@app.post("/api/workflow")
async def update_workflow(request: Request, manager: str = Depends(require_manager_auth)):
    payload = await request.json()
    wf_id = payload.get("workflow_id")
    steps = payload.get("steps", [])
    title = payload.get("title")
    window_title = payload.get("window_title")
    category = payload.get("category")

    update_fields = {"steps": steps}
    if title: update_fields["title"] = title
    if window_title: update_fields["window_title"] = window_title
    if category: update_fields["category"] = category

    if wf_id:
        workflow_collection.update_one({"workflow_id": wf_id}, {"$set": update_fields}, upsert=True)
        updated_doc = workflow_collection.find_one({"workflow_id": wf_id}, {"_id": 0})
    else:
        # Update first document as fallback
        workflow_collection.update_one({}, {"$set": update_fields}, upsert=True)
        updated_doc = workflow_collection.find_one({}, {"_id": 0})

    # Broadcast to all connected Lulu Desktop Clients in real-time (Zero-restart sync!)
    event_data = {
        "type": "WORKFLOW_UPDATED",
        "workflow": updated_doc
    }
    await ws_manager.broadcast_to_clients(event_data)
    await ws_manager.broadcast_to_dashboards(event_data)

    return {"status": "success", "message": "Workflow updated & pushed to active Lulu HUDs!", "workflow": updated_doc}

@app.post("/api/workflow/activate/{workflow_id}")
async def activate_workflow(workflow_id: str, manager: str = Depends(require_manager_auth)):
    target = workflow_collection.find_one({"workflow_id": workflow_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Target workflow not found")

    workflow_collection.update_many({}, {"$set": {"is_active": False}})
    workflow_collection.update_one({"workflow_id": workflow_id}, {"$set": {"is_active": True}})
    target["is_active"] = True

    event_data = {
        "type": "WORKFLOW_SWITCHED",
        "workflow": target
    }
    await ws_manager.broadcast_to_clients(event_data)
    await ws_manager.broadcast_to_dashboards(event_data)

    return {"status": "success", "message": f"Activated workflow: {target.get('title')}", "workflow": target}

@app.post("/api/workflows/create")
async def create_new_workflow(request: Request, manager: str = Depends(require_manager_auth)):
    payload = await request.json()
    wf_id = payload.get("workflow_id", "").strip()
    if not wf_id:
        raise HTTPException(status_code=400, detail="workflow_id is required")

    existing = workflow_collection.find_one({"workflow_id": wf_id})
    if existing:
        raise HTTPException(status_code=400, detail="Workflow ID already exists")

    new_wf = {
        "workflow_id": wf_id,
        "title": payload.get("title", "New Guide"),
        "window_title": payload.get("window_title", "Target Window"),
        "category": payload.get("category", "General"),
        "is_active": False,
        "steps": payload.get("steps", [])
    }
    workflow_collection.insert_one(new_wf)
    new_wf.pop("_id", None)

    await ws_manager.broadcast_to_dashboards({"type": "WORKFLOW_CREATED", "workflow": new_wf})
    return {"status": "success", "workflow": new_wf}


# ==========================================
# REAL-TIME TELEMETRY ENDPOINTS
# ==========================================
@app.get("/api/telemetry")
def get_telemetry():
    logs = list(telemetry_collection.find({}, {"_id": 0}).sort("_id", -1).limit(100))
    logs.reverse() # chronological order for rendering
    return logs

@app.post("/api/telemetry")
async def log_telemetry(request: Request):
    payload = await request.json()
    payload["timestamp"] = datetime.now().strftime("%H:%M:%S")
    telemetry_collection.insert_one(payload.copy())

    # ZERO-DELAY PUSH: Broadcast immediately to connected manager dashboards over WebSocket!
    safe_payload = {k: v for k, v in payload.items() if k != "_id"}
    await ws_manager.broadcast_to_dashboards({
        "type": "NEW_TELEMETRY",
        "data": safe_payload
    })

    return {"status": "logged", "timestamp": payload["timestamp"]}

@app.post("/api/telemetry/clear")
async def clear_telemetry(manager: str = Depends(require_manager_auth)):
    telemetry_collection.delete_many({})
    await ws_manager.broadcast_to_dashboards({"type": "TELEMETRY_CLEARED"})
    return {"status": "cleared"}


# ==========================================
# WEBSOCKET REAL-TIME ENDPOINTS
# ==========================================
@app.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    await ws_manager.connect_dashboard(websocket)
    try:
        while True:
            # Keep connection open; receive heartbeats / manager commands if any
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "PING":
                    await websocket.send_text(json.dumps({"type": "PONG"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect_dashboard(websocket)
    except Exception:
        ws_manager.disconnect_dashboard(websocket)


@app.websocket("/ws/client")
async def websocket_client_endpoint(websocket: WebSocket):
    await ws_manager.connect_client(websocket)
    try:
        # Send current active workflow to the newly connected desktop HUD client
        active_wf = get_active_workflow()
        await websocket.send_text(json.dumps({
            "type": "INITIAL_WORKFLOW",
            "workflow": active_wf
        }))

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # If desktop client reports telemetry over websocket, process & broadcast
                if msg.get("type") == "TELEMETRY_LOG":
                    telemetry_data = msg.get("data", {})
                    telemetry_data["timestamp"] = datetime.now().strftime("%H:%M:%S")
                    telemetry_collection.insert_one(telemetry_data.copy())
                    safe_data = {k: v for k, v in telemetry_data.items() if k != "_id"}
                    await ws_manager.broadcast_to_dashboards({
                        "type": "NEW_TELEMETRY",
                        "data": safe_data
                    })
            except Exception:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect_client(websocket)
    except Exception:
        await ws_manager.disconnect_client(websocket)


# ==========================================
# MANAGER WEB DASHBOARD SERVING
# ==========================================
@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    template_path = BASE_DIR / "templates" / "dashboard.html"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard template not found</h1>", status_code=404)


if __name__ == "__main__":
    print(f"[STARTUP] Starting Lulu Enterprise API Server on http://{SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run("server:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
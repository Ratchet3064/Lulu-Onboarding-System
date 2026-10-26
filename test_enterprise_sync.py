import sys
import time
import json
import asyncio
import requests
import websockets

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_URL = "http://127.0.0.1:5000"
WS_DASHBOARD_URL = "ws://127.0.0.1:5000/ws/dashboard"
WS_CLIENT_URL = "ws://127.0.0.1:5000/ws/client"

async def run_integration_tests():
    print("🧪 [Test 1/7] Testing Dashboard Web Page...")
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Dashboard failed with {r.status_code}"
    assert "LULU" in r.text, "Dashboard HTML missing LULU"
    print("  ✅ Dashboard rendered successfully.")

    print("🧪 [Test 2/7] Testing Multi-Workflow API...")
    r = requests.get(f"{BASE_URL}/api/workflows")
    assert r.status_code == 200, f"Workflows API failed with {r.status_code}"
    workflows = r.json()
    assert len(workflows) >= 2, f"Expected multiple workflows, found {len(workflows)}"
    print(f"  ✅ Found {len(workflows)} registered enterprise workflows:")
    for wf in workflows:
        print(f"     - [{wf.get('workflow_id')}] {wf.get('title')} (Active: {wf.get('is_active', False)})")

    print("🧪 [Test 3/7] Testing Manager JWT Authentication...")
    # Bad credentials
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert r.status_code == 401, "Expected 401 for bad password"
    
    # Good credentials
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "luluadmin123"})
    assert r.status_code == 200, "Login failed for valid admin credentials"
    token = r.json().get("access_token")
    assert token, "Missing access_token in login response"
    print("  ✅ Manager JWT authentication successful!")

    # Verify token
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    assert r.status_code == 200 and r.json().get("username") == "admin"
    print("  ✅ Bearer token authorization verified.")

    print("🧪 [Test 4/7] Testing WebSocket Dashboard Connection...")
    async with websockets.connect(WS_DASHBOARD_URL) as ws_dash:
        msg = await asyncio.wait_for(ws_dash.recv(), timeout=3.0)
        data = json.loads(msg)
        print(f"  ✅ Dashboard WebSocket received initial event: {data}")

        print("🧪 [Test 5/7] Testing WebSocket Client HUD Connection & Initial Workflow...")
        async with websockets.connect(WS_CLIENT_URL) as ws_client:
            client_msg = await asyncio.wait_for(ws_client.recv(), timeout=3.0)
            client_data = json.loads(client_msg)
            assert client_data.get("type") == "INITIAL_WORKFLOW"
            print(f"  ✅ Client received initial workflow: '{client_data.get('workflow', {}).get('title')}'")

            # Check if dashboard received client count update (should be >= 1)
            dash_client_count = await asyncio.wait_for(ws_dash.recv(), timeout=3.0)
            dash_count_data = json.loads(dash_client_count)
            assert dash_count_data.get("type") == "CLIENT_COUNT_UPDATE"
            print(f"  ✅ Dashboard notified of active client count: {dash_count_data.get('count')}")

            print("🧪 [Test 6/7] Testing Zero-Delay Telemetry Push over WebSocket...")
            telemetry_payload = {
                "step_num": 1,
                "target_button": "Open Customer Invoices",
                "duration_seconds": 3.4
            }
            # Post via HTTP API or WS
            requests.post(f"{BASE_URL}/api/telemetry", json=telemetry_payload)

            # Dashboard should receive instant notification over WS!
            instant_event = await asyncio.wait_for(ws_dash.recv(), timeout=3.0)
            dash_event = json.loads(instant_event)
            assert dash_event.get("type") == "NEW_TELEMETRY"
            assert dash_event.get("data", {}).get("duration_seconds") == 3.4
            print(f"  ✅ Dashboard flashed with live telemetry: {dash_event['data']['duration_seconds']}s")

            print("🧪 [Test 7/7] Testing Zero-Restart Workflow Sync (Manager -> Desktop Client)...")
            active_wf = requests.get(f"{BASE_URL}/api/workflow/active").json()
            test_steps = list(active_wf.get("steps", []))
            test_steps[0]["badge_text"] = "Step 1: Click 'Open Customer Invoices' [SYNC TEST]"
            
            # Manager saves workflow
            update_res = requests.post(
                f"{BASE_URL}/api/workflow", 
                json={"workflow_id": active_wf["workflow_id"], "steps": test_steps},
                headers=headers
            )
            assert update_res.status_code == 200

            # Client should receive WORKFLOW_UPDATED event immediately!
            client_update_msg = await asyncio.wait_for(ws_client.recv(), timeout=3.0)
            client_update_data = json.loads(client_update_msg)
            assert client_update_data.get("type") == "WORKFLOW_UPDATED"
            print(f"  ✅ Lulu Desktop Client HUD received real-time step update: '{client_update_data['workflow']['steps'][0]['badge_text']}'")

    print("\n🎉 ALL 7 ENTERPRISE INTEGRATION TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    asyncio.run(run_integration_tests())

import os
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Lulu Onboarding & Telemetry API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = os.path.join(os.path.dirname(__file__), "lulu_database.json")

DEFAULT_DB = {
    "workflow": {
        "workflow_id": "wf_refund_01",
        "title": "Customer Refund Onboarding Guide",
        "window_title": "Enterprise Billing Portal",
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
    "telemetry": []
}

def load_db():
    if not os.path.exists(DATA_FILE):
        save_db(DEFAULT_DB)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@app.get("/api/workflow")
def get_workflow():
    return load_db()["workflow"]

# NEW ENDPOINT: Save workflow updates from the dashboard
@app.post("/api/workflow")
async def update_workflow(request: Request):
    payload = await request.json()
    db = load_db()
    db["workflow"]["steps"] = payload.get("steps", [])
    save_db(db)
    return {"status": "success", "message": "Workflow deployed!"}

@app.get("/api/telemetry")
def get_telemetry():
    return load_db()["telemetry"]

@app.post("/api/telemetry")
async def log_telemetry(request: Request):
    payload = await request.json()
    db = load_db()
    payload["timestamp"] = datetime.now().strftime("%H:%M:%S")
    db["telemetry"].append(payload)
    save_db(db)
    return {"status": "logged"}

@app.post("/api/telemetry/clear")
def clear_telemetry():
    db = load_db()
    db["telemetry"] = []
    save_db(db)
    return {"status": "cleared"}

# ==========================================================
# MANAGER WEB DASHBOARD UI
# ==========================================================
@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Lulu Manager Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-[#0d0d16] text-white font-sans min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
        
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-pink-500/30 pb-5 mb-8">
            <div>
                <h1 class="text-3xl font-extrabold tracking-tight">
                    <span class="text-[#fc038c]">LULU</span> Enterprise Portal
                </h1>
                <p class="text-slate-400 text-sm mt-1">Real-Time Telemetry & Active Workflow Manager</p>
            </div>
            <button onclick="clearLogs()" class="bg-[#1e1e30] hover:bg-pink-600/20 border border-[#fc038c] text-pink-400 px-4 py-2 rounded-lg text-sm font-semibold transition">
                Reset Telemetry Data
            </button>
        </div>

        <!-- NEW: Live Workflow Builder -->
        <div class="mb-8 bg-[#151525] border border-emerald-500/30 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-[#fc038c]"></div>
            <div class="flex justify-between items-center mb-4">
                <div>
                    <h2 class="text-xl font-bold text-white">Live Workflow Builder</h2>
                    <p class="text-xs text-slate-400">Edit steps below. Click Save to instantly update Lulu's desktop HUD.</p>
                </div>
                <button onclick="saveWorkflow()" class="bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2 rounded-lg text-sm font-bold transition shadow-[0_0_15px_rgba(16,185,129,0.4)]">
                    💾 Save & Deploy to Lulu
                </button>
            </div>
            
            <div id="builderList" class="space-y-4"></div>
            
            <button onclick="addStep()" class="mt-4 w-full border-2 border-dashed border-slate-700 hover:border-emerald-500 text-slate-400 hover:text-emerald-400 py-3 rounded-xl transition font-bold">
                + Add New Step
            </button>
        </div>

        <!-- Telemetry & Analytics Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <div class="bg-[#151525] border border-slate-800 rounded-2xl p-6 shadow-xl">
                <h2 class="text-lg font-bold text-white mb-1">Step Bottlenecks (Seconds)</h2>
                <canvas id="telemetryChart" height="200"></canvas>
            </div>
            <div class="bg-[#151525] border border-slate-800 rounded-2xl p-6 shadow-xl">
                <h2 class="text-lg font-bold text-white mb-4">Live Employee Telemetry Log</h2>
                <div class="overflow-y-auto max-h-[250px] pr-2">
                    <table class="w-full text-left text-sm text-slate-300">
                        <thead class="text-xs uppercase bg-[#1e1e32] text-slate-400 sticky top-0">
                            <tr>
                                <th class="p-3">Step</th>
                                <th class="p-3">Duration</th>
                                <th class="p-3">Status</th>
                            </tr>
                        </thead>
                        <tbody id="logTableBody" class="divide-y divide-slate-800"></tbody>
                    </table>
                </div>
            </div>
        </div>

    </div>

    <script>
        let chartInstance = null;
        let builderSteps = [];

        // 1. Initial Load of Workflow for the Builder
        async function initBuilder() {
            const res = await fetch('/api/workflow');
            const wf = await res.json();
            builderSteps = wf.steps || [];
            renderBuilder();
        }

        // 2. Render the input fields
        function renderBuilder() {
            const container = document.getElementById('builderList');
            container.innerHTML = builderSteps.map((s, i) => `
                <div class="p-4 bg-[#1e1e30] border-l-4 border-[#fc038c] rounded-md grid grid-cols-1 md:grid-cols-2 gap-4 relative group">
                    <button onclick="deleteStep(${i})" class="absolute top-2 right-2 text-slate-500 hover:text-red-500 font-bold opacity-0 group-hover:opacity-100 transition">✕ Remove</button>
                    
                    <div>
                        <label class="text-xs text-slate-400 block mb-1">Target Button Name (Exact UI Match)</label>
                        <input type="text" class="w-full bg-[#0d0d16] border border-slate-700 text-white rounded p-2 text-sm focus:border-pink-500 outline-none" 
                            value="${s.target_button}" onchange="builderSteps[${i}].target_button = this.value">
                    </div>
                    <div>
                        <label class="text-xs text-slate-400 block mb-1">Success State Text (Done state)</label>
                        <input type="text" class="w-full bg-[#0d0d16] border border-slate-700 text-white rounded p-2 text-sm focus:border-pink-500 outline-none" 
                            value="${s.verify_screen_text}" onchange="builderSteps[${i}].verify_screen_text = this.value">
                    </div>
                    <div>
                        <label class="text-xs text-slate-400 block mb-1">Visual Badge Instruction</label>
                        <input type="text" class="w-full bg-[#0d0d16] border border-slate-700 text-white rounded p-2 text-sm focus:border-pink-500 outline-none" 
                            value="${s.badge_text}" onchange="builderSteps[${i}].badge_text = this.value">
                    </div>
                    <div>
                        <label class="text-xs text-slate-400 block mb-1">Edge-TTS Voice Narration</label>
                        <input type="text" class="w-full bg-[#0d0d16] border border-slate-700 text-[#38bdf8] rounded p-2 text-sm focus:border-pink-500 outline-none font-medium" 
                            value="${s.voice_text}" onchange="builderSteps[${i}].voice_text = this.value">
                    </div>
                </div>
            `).join('');
        }

        // 3. Add/Delete/Save functions
        function addStep() {
            builderSteps.push({
                step_num: builderSteps.length + 1,
                target_button: "New Button",
                badge_text: `Step ${builderSteps.length + 1}: Click New Button`,
                voice_text: "Please click the new button.",
                verify_screen_text: "New Button (Done)"
            });
            renderBuilder();
        }

        function deleteStep(index) {
            builderSteps.splice(index, 1);
            builderSteps.forEach((s, i) => s.step_num = i + 1); // Fix numbering
            renderBuilder();
        }

        async function saveWorkflow() {
            await fetch('/api/workflow', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ steps: builderSteps })
            });
            alert("✅ Workflow updated! Next time Lulu runs, she will download these new instructions.");
        }

        // 4. Live Telemetry Polling (Runs every 1.5s)
        async function fetchTelemetry() {
            const logRes = await fetch('/api/telemetry');
            const logs = await logRes.json();

            // Update Table
            const tbody = document.getElementById('logTableBody');
            tbody.innerHTML = logs.slice().reverse().map(l => {
                const isSlow = l.duration_seconds >= 8.0;
                const badge = isSlow 
                    ? `<span class="px-2 py-1 bg-pink-500/20 text-[#fc038c] border border-[#fc038c] rounded text-xs font-bold">⚠️ Slow</span>`
                    : `<span class="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-xs font-bold">✅ Smooth</span>`;
                return `
                    <tr>
                        <td class="p-3 font-bold text-sm">Step ${l.step_num}: ${l.target_button}</td>
                        <td class="p-3 font-bold text-white">${l.duration_seconds}s</td>
                        <td class="p-3">${badge}</td>
                    </tr>
                `;
            }).join('');

            // Update Chart
            const stepTimes = [];
            const stepLabels = [];
            logs.forEach(l => {
                stepTimes[l.step_num - 1] = l.duration_seconds;
                stepLabels[l.step_num - 1] = `Step ${l.step_num}`;
            });

            const colors = stepTimes.map(t => t >= 8.0 ? '#fc038c' : '#38bdf8');

            if (!chartInstance && stepTimes.length > 0) {
                const ctx = document.getElementById('telemetryChart').getContext('2d');
                chartInstance = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: stepLabels,
                        datasets: [{ label: 'Seconds', data: stepTimes, backgroundColor: colors, borderRadius: 6 }]
                    },
                    options: { scales: { y: { beginAtZero: true, grid: { color: '#26263a' } } }, plugins: { legend: { display: false } } }
                });
            } else if (chartInstance) {
                chartInstance.data.labels = stepLabels;
                chartInstance.data.datasets[0].data = stepTimes;
                chartInstance.data.datasets[0].backgroundColor = colors;
                chartInstance.update();
            }
        }

        async function clearLogs() {
            await fetch('/api/telemetry/clear', { method: 'POST' });
            if(chartInstance) { chartInstance.destroy(); chartInstance = null; }
            fetchTelemetry();
        }

        initBuilder();
        fetchTelemetry();
        setInterval(fetchTelemetry, 1500); 
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
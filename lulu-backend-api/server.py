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

# Default Database Seed
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
    db = load_db()
    return db["workflow"]

@app.post("/api/telemetry")
async def log_telemetry(request: Request):
    payload = await request.json()
    db = load_db()
    payload["timestamp"] = datetime.now().strftime("%H:%M:%S")
    db["telemetry"].append(payload)
    save_db(db)
    return {"status": "logged", "total_logs": len(db["telemetry"])}

@app.get("/api/telemetry")
def get_telemetry():
    db = load_db()
    return db["telemetry"]

@app.post("/api/telemetry/clear")
def clear_telemetry():
    db = load_db()
    db["telemetry"] = []
    save_db(db)
    return {"status": "cleared"}

# ==========================================================
# MANAGER WEB DASHBOARD UI (Served at http://localhost:5000)
# ==========================================================
@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Lulu Manager Dashboard - Workflow & Struggle Telemetry</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-[#0d0d16] text-white font-sans min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-pink-500/30 pb-5 mb-8">
            <div>
                <h1 class="text-3xl font-extrabold tracking-tight">
                    <span class="text-[#fc038c]">LULU</span> Enterprise Onboarding & Telemetry Portal
                </h1>
                <p class="text-slate-400 text-sm mt-1">Real-Time Employee Struggle Analytics & Active Workflow Manager</p>
            </div>
            <button onclick="clearLogs()" class="bg-[#1e1e30] hover:bg-pink-600/20 border border-[#fc038c] text-pink-400 px-4 py-2 rounded-lg text-sm font-semibold transition">
                Reset Telemetry Data
            </button>
        </div>

        <!-- Grid Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Left Card: Live Struggle & Hesitation Bar Chart -->
            <div class="bg-[#151525] border border-slate-800 rounded-2xl p-6 shadow-xl">
                <h2 class="text-lg font-bold text-white mb-1">Step Completion & Hesitation Bottlenecks (Seconds)</h2>
                <p class="text-xs text-slate-400 mb-4">Steps taking longer than 8s are flagged in Neon Pink (#fc038c) as UI bottlenecks.</p>
                <canvas id="telemetryChart" height="200"></canvas>
            </div>

            <!-- Right Card: Active Workflow Steps from Database -->
            <div class="bg-[#151525] border border-slate-800 rounded-2xl p-6 shadow-xl">
                <h2 class="text-lg font-bold text-white mb-1">Active Database Workflow</h2>
                <p class="text-xs text-slate-400 mb-4" id="wfTitle">Loading workflow...</p>
                <div id="stepsList" class="space-y-3"></div>
            </div>
        </div>

        <!-- Bottom Table: Live Employee Telemetry Feed -->
        <div class="mt-8 bg-[#151525] border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 class="text-lg font-bold text-white mb-4">Live Employee Step Telemetry Log</h2>
            <table class="w-full text-left text-sm text-slate-300">
                <thead class="text-xs uppercase bg-[#1e1e32] text-slate-400">
                    <tr>
                        <th class="p-3">Time</th>
                        <th class="p-3">Step</th>
                        <th class="p-3">Target Button</th>
                        <th class="p-3">Duration (s)</th>
                        <th class="p-3">Bottleneck Status</th>
                    </tr>
                </thead>
                <tbody id="logTableBody" class="divide-y divide-slate-800"></tbody>
            </table>
        </div>
    </div>

    <script>
        let chartInstance = null;

        async function fetchDashboardData() {
            const wfRes = await fetch('/api/workflow');
            const wf = await wfRes.json();
            document.getElementById('wfTitle').innerText = `Target Window: "${wf.window_title}" — ${wf.title}`;

            const stepsHtml = wf.steps.map(s => `
                <div class="p-3 bg-[#1e1e30] border-l-4 border-[#fc038c] rounded-md">
                    <div class="font-bold text-sm text-white">Step ${s.step_num}: ${s.target_button}</div>
                    <div class="text-xs text-slate-400 mt-1">Voice: "${s.voice_text}"</div>
                </div>
            `).join('');
            document.getElementById('stepsList').innerHTML = stepsHtml;

            const logRes = await fetch('/api/telemetry');
            const logs = await logRes.json();

            // Update Table
            const tbody = document.getElementById('logTableBody');
            tbody.innerHTML = logs.slice().reverse().map(l => {
                const isSlow = l.duration_seconds >= 8.0;
                const badge = isSlow 
                    ? `<span class="px-2 py-1 bg-pink-500/20 text-[#fc038c] border border-[#fc038c] rounded text-xs font-bold">⚠️ UI Bottleneck (Slow)</span>`
                    : `<span class="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-xs font-bold">✅ Smooth</span>`;
                return `
                    <tr>
                        <td class="p-3 font-mono text-xs">${l.timestamp}</td>
                        <td class="p-3 font-bold">Step ${l.step_num}</td>
                        <td class="p-3">${l.target_button}</td>
                        <td class="p-3 font-bold text-white">${l.duration_seconds}s</td>
                        <td class="p-3">${badge}</td>
                    </tr>
                `;
            }).join('');

            // Compute average or latest time per step for Chart
            const stepTimes = [0, 0, 0];
            logs.forEach(l => {
                if (l.step_num >= 1 && l.step_num <= 3) {
                    stepTimes[l.step_num - 1] = l.duration_seconds;
                }
            });

            const colors = stepTimes.map(t => t >= 8.0 ? '#fc038c' : '#38bdf8');

            if (!chartInstance) {
                const ctx = document.getElementById('telemetryChart').getContext('2d');
                chartInstance = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['Step 1: Open Invoices', 'Step 2: Verify Balance', 'Step 3: Issue Refund'],
                        datasets: [{
                            label: 'Completion Time (Seconds)',
                            data: stepTimes,
                            backgroundColor: colors,
                            borderRadius: 8
                        }]
                    },
                    options: {
                        scales: { y: { beginAtZero: true, grid: { color: '#26263a' } } },
                        plugins: { legend: { display: false } }
                    }
                });
            } else {
                chartInstance.data.datasets[0].data = stepTimes;
                chartInstance.data.datasets[0].backgroundColor = colors;
                chartInstance.update();
            }
        }

        async function clearLogs() {
            await fetch('/api/telemetry/clear', { method: 'POST' });
            fetchDashboardData();
        }

        fetchDashboardData();
        setInterval(fetchDashboardData, 1500); // Live auto-refresh every 1.5s!
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
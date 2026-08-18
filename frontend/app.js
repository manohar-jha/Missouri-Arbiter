// Missouri Arbiter Single Page Application Logic
// Mission Control x SpaceX Maritime Operations Interface

document.addEventListener("DOMContentLoaded", () => {
    checkHealth();
    refreshAllData();
    initRadarAnimation();
    
    // Set up auto-refresh every 15 seconds
    setInterval(refreshAllData, 15000);
});

// TAB SWITCHING ROUTER
function switchTab(tabId) {
    document.querySelectorAll(".nav-tab").forEach(tab => {
        tab.classList.toggle("active", tab.getAttribute("data-tab") === tabId);
    });

    document.querySelectorAll(".tab-view").forEach(view => {
        view.classList.toggle("active", view.id === `view-${tabId}`);
        view.classList.toggle("hidden", view.id !== `view-${tabId}`);
    });

    if (tabId === "fleet") {
        loadFleetMatrix();
    } else if (tabId === "traffic") {
        initRadarAnimation();
    } else if (tabId === "ledger") {
        refreshLedger();
    }
}

// HEALTH CHECK & INFRASTRUCTURE STATUS
async function checkHealth() {
    try {
        const resp = await fetch("/health");
        const data = await resp.json();

        const dbPill = document.getElementById("dbInfraPill");
        if (data.cockroachdb_status && data.cockroachdb_status.includes("CONNECTED")) {
            dbPill.innerHTML = `
                <span class="pill-dot dot-green"></span>
                <span class="pill-label">COCKROACHDB</span>
                <span class="pill-val">CLOUD CONNECTED</span>
            `;
        } else {
            dbPill.innerHTML = `
                <span class="pill-dot dot-rose"></span>
                <span class="pill-label">COCKROACHDB</span>
                <span class="pill-val">${data.cockroachdb_status}</span>
            `;
        }
    } catch (e) {
        console.error("Health check error:", e);
    }
}

// COMBINED DATA REFRESH
function refreshAllData() {
    refreshCorridors();
    refreshLedger();
    fetchTelemetryMetrics();
}

// TELEMETRY METRICS STRIP
async function fetchTelemetryMetrics() {
    try {
        const [vesselsRes, channelsRes, resRes, ledgerRes] = await Promise.all([
            fetch("/api/vessels").then(r => r.json()).catch(() => ({})),
            fetch("/api/channels").then(r => r.json()).catch(() => ({})),
            fetch("/api/reservations").then(r => r.json()).catch(() => ({})),
            fetch("/api/ledger").then(r => r.json()).catch(() => ({}))
        ]);

        if (vesselsRes.status === "SUCCESS" && vesselsRes.vessels) {
            document.getElementById("valFleetCount").textContent = vesselsRes.vessels.length;
        }
        if (channelsRes.status === "SUCCESS" && channelsRes.channels) {
            document.getElementById("valCorridorCount").textContent = Object.keys(channelsRes.channels).length;
        }
        if (resRes.status === "SUCCESS" && resRes.reservations) {
            document.getElementById("valReservationsCount").textContent = resRes.reservations.length;
        }
        if (ledgerRes.status === "SUCCESS" && ledgerRes.ledger_entries) {
            document.getElementById("valLedgerCount").textContent = ledgerRes.ledger_entries.length;
        }
    } catch (e) {
        console.error("Telemetry fetch error:", e);
    }
}

// PRESET SCENARIO TRIGGERS
const PRESET_SCENARIOS = {
    1: "Vessel 'ship_alpha' (draft 11.5 meters) requests passage through channel 'ch_main'. Inspect vessel dimensions, channel limits, check restrictions, select a tug if required, make reservation if feasible, and record the decision into the decision ledger.",
    2: "Vessel 'ship_beta' with draft 10.0 meters needs to navigate through 'ch_main'. Check channel restrictions for 'ch_main', inspect alternative channel 'ch_north', determine appropriate routing decision, and log decision to the ledger.",
    3: "A severe storm with high crosswinds of 30 knots is affecting navigation near channel 'ch_main'. Search historical hydrodynamic memory for previous maneuver experiences under severe wind conditions, and synthesize operational advice."
};

function runScenario(num) {
    const text = PRESET_SCENARIOS[num];
    if (text) {
        document.getElementById("promptInput").value = text;
        submitAgentQuery();
    }
}

// AGENT QUERY SUBMISSION & TRACE LOG
async function submitAgentQuery() {
    const promptText = document.getElementById("promptInput").value.trim();
    if (!promptText) {
        alert("Please enter a command or select a mission scenario.");
        return;
    }

    const btn = document.getElementById("btnSubmit");
    const spinner = document.getElementById("spinner");
    const traceLog = document.getElementById("traceLog");
    const decisionCard = document.getElementById("decisionCard");
    const decisionText = document.getElementById("decisionText");

    btn.disabled = true;
    spinner.classList.remove("hidden");
    traceLog.innerHTML = `<div class="term-line"><span class="txt-cyan">[AWS BEDROCK + MCP]</span> Initializing multi-turn agent tool reasoning loop...</div>`;
    decisionCard.classList.add("hidden");

    try {
        const resp = await fetch("/api/agent/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: promptText })
        });
        const data = await resp.json();

        btn.disabled = false;
        spinner.classList.add("hidden");

        if (data.status === "SUCCESS" || data.status === "COMPLETED_MAX_TURNS") {
            // Render Decision Briefing Card
            decisionCard.classList.remove("hidden");
            decisionText.innerHTML = parseMarkdownToHtml(data.response);

            // Parse decision metadata
            const decisionBadge = document.getElementById("decisionBadge");
            if (data.response.includes("REROUTED")) {
                decisionBadge.textContent = "REROUTED";
                decisionBadge.style.color = "var(--amber-warning)";
                decisionBadge.style.borderColor = "var(--amber-warning)";
            } else if (data.response.includes("ADVISORY") || data.response.includes("Guidance")) {
                decisionBadge.textContent = "TACTICAL ADVISORY";
                decisionBadge.style.color = "var(--blue-accent)";
                decisionBadge.style.borderColor = "var(--blue-accent)";
            } else {
                decisionBadge.textContent = "PASSAGE APPROVED";
                decisionBadge.style.color = "var(--green-status)";
                decisionBadge.style.borderColor = "var(--green-status)";
            }

            // Render Execution Trace
            if (data.tool_execution_trace && data.tool_execution_trace.length > 0) {
                let traceHtml = "";
                data.tool_execution_trace.forEach(t => {
                    traceHtml += `
                        <div class="trace-item">
                            <span class="trace-tool">[TURN ${t.turn}] MCP TOOL CALL: ${t.tool_name}</span>
                            <div><span class="txt-muted">PARAMS:</span> <code>${t.arguments}</code></div>
                            <div><span class="txt-muted">RESULT:</span> <span class="txt-green">${t.result ? (t.result.status || 'SUCCESS') : 'OK'}</span></div>
                        </div>
                    `;
                });
                traceLog.innerHTML = traceHtml;
            } else {
                traceLog.innerHTML = `<div class="term-line">Agent completed reasoning directly without external tool invocation.</div>`;
            }

            refreshAllData();
        } else {
            alert("Agent processing error: " + (data.detail || data.message || "Unknown error"));
        }
    } catch (e) {
        btn.disabled = false;
        spinner.classList.add("hidden");
        console.error("Agent query error:", e);
        alert("Failed to connect to Missouri Arbiter backend service.");
    }
}

// SIMPLE MARKDOWN PARSER FOR DECISION CONTENT
function parseMarkdownToHtml(mdText) {
    if (!mdText) return "";
    let html = mdText
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h2>$1</h2>')
        .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
        .replace(/`(.*?)`/gim, '<code>$1</code>')
        .replace(/\n\n/gim, '<br><br>')
        .replace(/\n/gim, '<br>');
    return html;
}

// REFRESH CORRIDORS & HAZARDS
async function refreshCorridors() {
    try {
        const resp = await fetch("/api/channels");
        const data = await resp.json();
        const container = document.getElementById("corridorCards");

        if (data.status === "SUCCESS") {
            let html = "";
            const channels = data.channels || {};
            const restrs = data.restrictions || {};

            for (const key in channels) {
                const ch = channels[key];
                const isRestricted = !!restrs[key];
                const restrText = isRestricted ? `⚠️ RESTRICTED: ${restrs[key].reason || 'Storm Closure'}` : "🟢 OPEN / NORMAL DRAFT";

                html += `
                    <div class="corridor-card ${isRestricted ? 'restricted' : ''}">
                        <div class="cc-name">${ch.name} (${key})</div>
                        <div class="cc-stat">Max Draft: <strong>${ch.max_draft}m</strong> | Width: ${ch.width_meters}m</div>
                        <div class="cc-stat" style="margin-top: 4px;">${restrText}</div>
                    </div>
                `;
            }
            container.innerHTML = html;
        }
    } catch (e) {
        console.error("Refresh corridors error:", e);
    }
}

// INJECT STORM HAZARD FROM UI
async function injectClosureFromUI() {
    const chId = document.getElementById("selHazardChannel").value;
    try {
        const resp = await fetch("/api/simulator/inject-closure", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                channel_id: chId,
                reason: "Severe Shoaling & High Winds 30 knots",
                max_draft_limit: 8.0
            })
        });
        const res = await resp.json();
        if (res.status === "SUCCESS") {
            alert(`Hazard restriction injected into ${chId}! Max draft reduced to 8.0m.`);
            refreshCorridors();
        }
    } catch (e) {
        console.error("Hazard injection error:", e);
    }
}

// STEP SIMULATION FROM UI
async function stepSimulationUI() {
    try {
        const resp = await fetch("/api/simulator/step", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ delta_seconds: 60.0 })
        });
        const res = await resp.json();
        if (res.status === "SUCCESS") {
            refreshAllData();
        }
    } catch (e) {
        console.error("Simulation step error:", e);
    }
}

// FLEET MATRIX LOAD
async function loadFleetMatrix() {
    try {
        const resp = await fetch("/api/vessels");
        const data = await resp.json();
        const tbody = document.getElementById("fleetTableBody");

        if (data.status === "SUCCESS" && data.vessels) {
            let html = "";
            data.vessels.forEach(v => {
                html += `
                    <tr onclick="selectVesselForInspection('${v.vessel_id}', '${v.name}', ${v.draft}, ${v.length}, ${v.speed})">
                        <td><strong>${v.vessel_id}</strong></td>
                        <td>${v.name}</td>
                        <td>CONTAINER / TANKER</td>
                        <td>${v.length}m</td>
                        <td><span class="txt-cyan">${v.draft}m</span></td>
                        <td>${v.speed} kts</td>
                        <td><span class="badge-status status-underway">${v.status || 'UNDERWAY'}</span></td>
                        <td>${v.channel_id || 'ch_main'}</td>
                        <td><button class="btn-tech" style="padding: 2px 8px; font-size: 10px;">Inspect</button></td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        }
    } catch (e) {
        console.error("Fleet matrix error:", e);
    }
}

function selectVesselForInspection(id, name, draft, length, speed) {
    document.getElementById("inspVesselName").textContent = name.toUpperCase();
    document.getElementById("inspVesselID").textContent = `ID: ${id} | AIS ACTIVE`;
    document.getElementById("inspDraft").textContent = `${draft} meters`;
    document.getElementById("inspLength").textContent = `${length} meters`;
    document.getElementById("inspSpeed").textContent = `${speed} knots`;
    calculateUkcFromUI(draft);
}

function calculateUkcFromUI(customDraft) {
    const selCh = document.getElementById("selUkcChannel").value;
    const maxDrafts = { "ch_main": 12.0, "ch_north": 10.5, "ch_south": 11.0 };
    const vesselDraft = customDraft || 11.5;
    const maxAllowed = maxDrafts[selCh] || 12.0;
    const margin = maxAllowed - vesselDraft;

    const resultBox = document.getElementById("ukcResult");
    if (margin >= 0) {
        resultBox.innerHTML = `Under-Keel Margin: <span class="txt-green">+${margin.toFixed(1)}m</span> | Safe Corridor Transit`;
    } else {
        resultBox.innerHTML = `Under-Keel Margin: <span class="txt-amber">${margin.toFixed(1)}m EXCEEDED</span> | Tug Escort / Reroute Required`;
    }
}

// DECISION LEDGER TABLE
async function refreshLedger() {
    try {
        const resp = await fetch("/api/ledger");
        const data = await resp.json();
        const tbody = document.getElementById("ledgerTableBody");

        if (data.status === "SUCCESS" && data.ledger_entries && data.ledger_entries.length > 0) {
            let html = "";
            data.ledger_entries.forEach(row => {
                const ts = row.timestamp || row.created_at;
                const created = ts ? new Date(ts).toLocaleTimeString() : "N/A";
                const eventType = row.event_type || row.decision_type || "DECISION";
                const summary = row.summary || row.recommendation || "";
                let risk = row.risk_score;
                if (risk === undefined && row.details) {
                    try {
                        const d = typeof row.details === 'string' ? JSON.parse(row.details) : row.details;
                        risk = d.risk_score;
                    } catch(e) {}
                }

                html += `
                    <tr>
                        <td>${created}</td>
                        <td><strong>${row.vessel_id || 'N/A'}</strong></td>
                        <td>${row.channel_id || 'N/A'}</td>
                        <td><span class="badge-decision">${eventType}</span></td>
                        <td style="max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${summary}</td>
                        <td><span class="txt-green">${risk !== undefined ? risk : 0.15}</span></td>
                        <td><code style="font-size: 10px;">${(row.ledger_id || row.decision_id || 'N/A').toString().substring(0, 8)}</code></td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        } else {
            tbody.innerHTML = `<tr><td colspan="7" class="loading-text">No decision ledger records found in CockroachDB Cloud.</td></tr>`;
        }
    } catch (e) {
        console.error("Refresh ledger error:", e);
    }
}

// RADAR CANVAS ANIMATION
let radarSweepAngle = 0;
function initRadarAnimation() {
    const canvas = document.getElementById("radarCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    function drawRadar() {
        const w = canvas.width;
        const h = canvas.height;
        const cx = w / 2;
        const cy = h / 2;
        const maxR = Math.min(w, h) / 2 - 20;

        ctx.clearRect(0, 0, w, h);

        // Background dark gradient
        const bgGrad = ctx.createRadialGradient(cx, cy, 10, cx, cy, maxR);
        bgGrad.addColorStop(0, "#080F1D");
        bgGrad.addColorStop(1, "#03060C");
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, w, h);

        // Concentric radar rings
        ctx.strokeStyle = "rgba(0, 240, 255, 0.25)";
        ctx.lineWidth = 1;
        for (let r = maxR / 4; r <= maxR; r += maxR / 4) {
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.stroke();
        }

        // Crosshairs
        ctx.beginPath();
        ctx.moveTo(cx - maxR, cy); ctx.lineTo(cx + maxR, cy);
        ctx.moveTo(cx, cy - maxR); ctx.lineTo(cx, cy + maxR);
        ctx.stroke();

        // Draw Missouri River Corridor Waypoint Polylines
        ctx.strokeStyle = "rgba(56, 189, 248, 0.5)";
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);

        // Main Channel (ch_main)
        ctx.beginPath();
        ctx.moveTo(cx - 180, cy + 120);
        ctx.lineTo(cx, cy);
        ctx.lineTo(cx + 180, cy - 120);
        ctx.stroke();

        // North Bypass (ch_north)
        ctx.strokeStyle = "rgba(0, 240, 255, 0.35)";
        ctx.beginPath();
        ctx.moveTo(cx - 180, cy + 120);
        ctx.lineTo(cx - 50, cy - 100);
        ctx.lineTo(cx + 180, cy - 120);
        ctx.stroke();

        ctx.setLineDash([]); // Reset line dash

        // Draw Vessel Blips
        // Vessel 1: ship_alpha
        drawVesselBlip(ctx, cx - 60, cy + 40, "ship_alpha (11.5m)", "#00F0FF");
        // Vessel 2: ship_beta
        drawVesselBlip(ctx, cx + 70, cy - 45, "ship_beta (10.0m)", "#10B981");

        // Rotating Sweep Line
        radarSweepAngle += 0.015;
        if (radarSweepAngle > Math.PI * 2) radarSweepAngle = 0;

        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(radarSweepAngle);

        const sweepGrad = ctx.createConicGradient(0, 0, 0);
        sweepGrad.addColorStop(0, "rgba(0, 240, 255, 0.4)");
        sweepGrad.addColorStop(0.1, "rgba(0, 240, 255, 0.05)");
        sweepGrad.addColorStop(1, "transparent");

        ctx.fillStyle = sweepGrad;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.arc(0, 0, maxR, 0, Math.PI / 3, false);
        ctx.closePath();
        ctx.fill();

        ctx.restore();

        requestAnimationFrame(drawRadar);
    }

    requestAnimationFrame(drawRadar);
}

function drawVesselBlip(ctx, x, y, label, color) {
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.font = "10px 'JetBrains Mono', monospace";
    ctx.fillStyle = "#FFFFFF";
    ctx.fillText(label, x + 10, y + 4);
}

// SCROLL SMOOTHLY TO COMMAND CONSOLE
function scrollToConsole() {
    const input = document.getElementById("promptInput");
    if (input) {
        input.scrollIntoView({ behavior: "smooth", block: "center" });
        input.focus();
    }
}

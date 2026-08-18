import urllib.request
import json
import re

def verify_frontend():
    print("==================================================")
    print("VERIFYING FRONTEND INTEGRATION & NO GROQ REFERENCES")
    print("==================================================")

    # 1. Fetch index.html
    with urllib.request.urlopen("http://localhost:8000/") as resp:
        html = resp.read().decode("utf-8")
        assert resp.status == 200, "GET / failed"
        print("[PASS] GET / -> 200 OK")
        
        # Verify brand & pills
        assert "MISSOURI ARBITER" in html, "Brand title missing"
        assert "AWS BEDROCK" in html, "AWS BEDROCK pill missing"
        assert "MCP SERVER" in html, "MCP SERVER pill missing"
        assert "COCKROACHDB" in html, "COCKROACHDB pill missing"
        assert "COMMAND CENTER" in html, "COMMAND CENTER tab missing"
        assert "FLEET INTELLIGENCE" in html, "FLEET INTELLIGENCE tab missing"
        assert "SITUATIONAL AWARENESS" in html, "SITUATIONAL AWARENESS tab missing"
        assert "AI MISSION OPS" in html, "AI MISSION OPS tab missing"
        assert "DECISION LEDGER" in html, "DECISION LEDGER tab missing"
        
        # Verify NO Groq references
        assert "groq" not in html.lower(), "Found 'groq' reference in index.html!"
        print("[PASS] index.html contains all brand elements & 0 Groq references!")

    # 2. Fetch app.js
    with urllib.request.urlopen("http://localhost:8000/static/app.js") as resp:
        js = resp.read().decode("utf-8")
        assert resp.status == 200, "GET /static/app.js failed"
        assert "groq" not in js.lower(), "Found 'groq' reference in app.js!"
        print("[PASS] app.js loaded -> 0 Groq references!")

    # 3. Fetch styles.css
    with urllib.request.urlopen("http://localhost:8000/static/styles.css") as resp:
        css = resp.read().decode("utf-8")
        assert resp.status == 200, "GET /static/styles.css failed"
        assert "groq" not in css.lower(), "Found 'groq' reference in styles.css!"
        print("[PASS] styles.css loaded -> 0 Groq references!")

    # 3b. Verify 3 Cargo Ship Images load via HTTP 200 OK
    for img_name in ["ship1.png", "ship2.png", "ship3.png"]:
        url = f"http://localhost:8000/static/images/{img_name}"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200, f"GET {url} failed!"
            print(f"[PASS] Cargo Ship Image loaded: {img_name} ({len(resp.read())} bytes)")

    # 4. Check Health endpoint
    with urllib.request.urlopen("http://localhost:8000/health") as resp:
        health = json.loads(resp.read().decode("utf-8"))
        print(f"[PASS] GET /health -> CockroachDB Status: {health.get('cockroachdb_status')}")

    # 5. Check API Channels
    with urllib.request.urlopen("http://localhost:8000/api/channels") as resp:
        ch = json.loads(resp.read().decode("utf-8"))
        assert ch.get("status") == "SUCCESS"
        print(f"[PASS] GET /api/channels -> {len(ch.get('channels', {}))} corridors available")

    # 6. Check API Vessels
    with urllib.request.urlopen("http://localhost:8000/api/vessels") as resp:
        v = json.loads(resp.read().decode("utf-8"))
        assert v.get("status") == "SUCCESS"
        print(f"[PASS] GET /api/vessels -> {len(v.get('vessels', []))} vessels tracked")

    # 7. Check API Ledger
    with urllib.request.urlopen("http://localhost:8000/api/ledger") as resp:
        l = json.loads(resp.read().decode("utf-8"))
        assert l.get("status") == "SUCCESS"
        print(f"[PASS] GET /api/ledger -> {len(l.get('ledger_entries', []))} ledger audit records")

    print("\n==================================================")
    print("ALL FRONTEND VERIFICATION CHECKS PASSED 100%")
    print("==================================================")

if __name__ == "__main__":
    verify_frontend()

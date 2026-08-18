import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def test_query(label, prompt_text):
    print(f"\n==================================================")
    print(f"TESTING QUERY {label}")
    print(f"==================================================")
    payload = {"prompt": prompt_text}
    req = urllib.request.Request(
        "http://localhost:8000/api/agent/query",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"Query {label} Status:", res.get("status"))
        print("Turns taken:", res.get("turns_taken"))
        print("Tool Trace:")
        for t in res.get("tool_execution_trace", []):
            print(f"  - {t['tool_name']}({t['arguments']}) -> {t['result'].get('status')}")
        print("Response snippet:", res.get("response", "")[:200])
        assert res.get("status") == "SUCCESS", f"Query {label} failed: {res}"

if __name__ == "__main__":
    prompt_a = "Vessel 'ship_alpha' (draft 11.5 meters) requests passage through channel 'ch_main'. Inspect vessel dimensions, channel limits, check restrictions, select a tug if required, make reservation if feasible, and record the decision into the decision ledger."
    prompt_b = "Vessel 'ship_beta' with draft 10.0 meters needs to navigate through 'ch_main'. Check channel restrictions for 'ch_main', inspect alternative channel 'ch_north', determine appropriate routing decision, and log decision to the ledger."
    prompt_c = "A severe storm with high crosswinds of 30 knots is affecting navigation near channel 'ch_main'. Search historical hydrodynamic memory for previous maneuver experiences under severe wind conditions, and synthesize operational advice."
    
    test_query("A (Deep Draft)", prompt_a)
    test_query("B (Rerouting)", prompt_b)
    test_query("C (Hydrodynamic Memory with Decimal Fields)", prompt_c)

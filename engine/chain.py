"""Bridge between the Python app and the Hardhat chain (persistent local node on 127.0.0.1:8545).

Attack Mode tries the real contract first; if Node/Hardhat is unavailable it falls back to the Python
mirror of the same rules (engine.match.classify) and says so in the result (`source`).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request

from .common import OUT, ROOT

HOST, PORT = "127.0.0.1", 8545
REVERT_CODE = {"NOT_OWNER": "DOUBLE_SOLD / not owner", "NOT_ISSUED": "UNISSUED", "DOUBLE_CLAIM": "DOUBLE_RETIRED (second claim)",
               "ALREADY_RETIRED": "DOUBLE_RETIRED", "RETIRED": "RETIRED credits", "HOST_DOUBLE_CLAIM": "ARTICLE6_DOUBLE_CLAIM",
               "OVERLAP_ISSUANCE": "OVERLAP_ISSUANCE"}


def _npx():
    return shutil.which("npx") or shutil.which("npx.cmd")


def node_alive() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _rpc(method, params):
    req = urllib.request.Request(f"http://{HOST}:{PORT}", data=json.dumps(dict(jsonrpc="2.0", id=1, method=method, params=params)).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())["result"]


def chain_ready() -> bool:
    f = OUT / "chain_replay.json"
    if not (node_alive() and f.exists()):
        return False
    try:
        rep = json.loads(f.read_text(encoding="utf-8"))
        import hashlib
        cur = hashlib.sha256((OUT / "reconciliation_events.csv").read_bytes()).hexdigest()
        if rep.get("events_sha256") != cur:   # ledger changed since the replay: the on-chain state is stale
            return False
        return rep.get("network") == "localhost" and _rpc("eth_getCode", [rep["contract"], "latest"]) not in ("0x", None)
    except Exception:
        return False


def toolchain_available() -> bool:
    return bool(_npx()) and (ROOT / "node_modules" / "hardhat").exists()


def ensure_chain(log=print) -> bool:
    """Start a local node (if needed) and replay the ledger on it. Returns True when the real contract is live."""
    if chain_ready():
        return True
    if not toolchain_available():
        return False
    env = dict(os.environ, VERDIQ_REPLAY="1")
    if not node_alive():
        log("starting local Hardhat node…")
        logf = open(OUT / "hardhat_node.log", "w")
        flags = 0x00000200 if os.name == "nt" else 0   # CREATE_NEW_PROCESS_GROUP
        subprocess.Popen([_npx(), "hardhat", "node", "--hostname", HOST, "--port", str(PORT)], cwd=ROOT, env=env,
                         stdout=logf, stderr=logf, creationflags=flags)
        for _ in range(60):
            if node_alive():
                break
            time.sleep(0.5)
        else:
            return False
    else:
        try:
            _rpc("hardhat_reset", [])   # a node from an earlier session: start from a clean chain so timestamps can replay
        except Exception:
            pass
    log("replaying ledger on-chain…")
    r = subprocess.run([_npx(), "hardhat", "run", "scripts/replay.js", "--network", "localhost"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=600)
    return r.returncode == 0 and chain_ready()


def stop_node():
    """Best-effort: ask the OS to stop whatever listens on the Hardhat port (used by `make clean`)."""
    if os.name == "nt":
        subprocess.run('for /f "tokens=5" %a in (\'netstat -aon ^| findstr :8545 ^| findstr LISTENING\') do taskkill /F /PID %a', shell=True,
                       capture_output=True)


SEL_TRANSFER, SEL_RETIRE = "4ccf16da", "aafe020a"          # keccak4 of transfer(uint64,uint64,address) / retire(uint64,uint64,bytes32)
KNOWN_CLAIMS = {"FY2026 net-zero claim": "0d1d1e74eede5959e844ed34164d92e22d8223e06521d461f7eeb70270defb63"}   # keccak256 of the claim text


def _rpc_raw(method, params):
    req = urllib.request.Request(f"http://{HOST}:{PORT}", data=json.dumps(dict(jsonrpc="2.0", id=1, method=method, params=params)).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def _fire_rpc(spec: dict):
    """Direct JSON-RPC to the local node (no Node.js process): ~50 ms. Returns None if the spec needs the script path."""
    import re
    rep = json.loads((OUT / "chain_replay.json").read_text(encoding="utf-8"))
    parties = rep["parties"]
    actor = parties.get(spec["actor"])
    if not actor:
        return None
    w = lambda n: format(int(n), "064x")
    if spec["kind"] == "TRADE":
        to = parties.get(spec["counterparty"])
        if not to:
            return None
        data = "0x" + SEL_TRANSFER + w(spec["start"]) + w(spec["end"]) + to[2:].lower().rjust(64, "0")
    else:
        h = KNOWN_CLAIMS.get(spec["counterparty"])
        if not h:
            return None
        data = "0x" + SEL_RETIRE + w(spec["start"]) + w(spec["end"]) + h
    t0 = time.time()
    _rpc("hardhat_impersonateAccount", [actor])
    _rpc("hardhat_setBalance", [actor, "0x56BC75E2D63100000"])
    tx = {"from": actor, "to": rep["contract"], "data": data, "gas": hex(15_000_000)}
    call = _rpc_raw("eth_call", [tx, "latest"])
    reason = ""
    if "error" in call:
        m = re.search(r"reason string '([^']+)'", json.dumps(call["error"]))
        reason = m.group(1) if m else "REVERTED"
    txh = _rpc("eth_sendTransaction", [tx])
    rc = None
    for _ in range(40):
        rc = _rpc("eth_getTransactionReceipt", [txh])
        if rc:
            break
        time.sleep(0.05)
    if not rc:
        return None
    blk = _rpc("eth_getBlockByNumber", [rc["blockNumber"], False])
    ok = int(rc["status"], 16) == 1
    return dict(source="hardhat-node", contract=rep["contract"], accepted=ok, reason="" if ok else reason, txHash=txh,
                block=int(rc["blockNumber"], 16), gasUsed=int(rc["gasUsed"], 16), ms=int((time.time() - t0) * 1000),
                chainTime=int(blk["timestamp"], 16))


def fire_attack(spec: dict, ledger, classify_fn) -> dict:
    """spec: kind, actor, counterparty, start, end. Tries the real chain, falls back to the Python mirror."""
    if chain_ready():
        try:
            res = _fire_rpc(spec)
            if res:
                return res
        except Exception:
            pass
        env = dict(os.environ, ATTACK_SPEC=json.dumps(spec), VERDIQ_REPLAY="1")
        try:
            r = subprocess.run([_npx(), "hardhat", "run", "scripts/attack.js", "--network", "localhost"], cwd=ROOT, env=env,
                               capture_output=True, text=True, timeout=120)
            line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), None)
            if line:
                res = json.loads(line[7:])
                if "error" not in res:
                    return res
        except Exception:
            pass
    t0 = time.time()
    st, why = classify_fn(ledger, spec["kind"], spec["start"], spec["end"], spec["actor"])
    fake = "0x" + hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    return dict(source="python-simulation", accepted=st == "MATCHED", reason={"DOUBLE_SOLD": "NOT_OWNER", "ORPHAN": "NOT_OWNER", "UNISSUED": "NOT_ISSUED",
                "DOUBLE_RETIRED": "ALREADY_RETIRED", "RETIRED_NOT_OWNED": "NOT_OWNER"}.get(st, ""), txHash=fake, block=None,
                gasUsed=None, ms=int((time.time() - t0) * 1000), note="Hardhat node unavailable - Python mirror of the contract rules was used.")


def onchain_root(date_iso: str):
    """Root anchored on the live chain for a close date (None if the chain is offline / not anchored)."""
    if not chain_ready():
        return None
    env = dict(os.environ, CLOSE_DATE=date_iso.replace("-", ""), VERDIQ_REPLAY="1")
    r = subprocess.run([_npx(), "hardhat", "run", "scripts/onchain.js", "--network", "localhost"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("ROOT ")), "ROOT error")[5:].strip()
    return None if line in ("none", "error") else line

#!/usr/bin/env python3
"""One turn of a Claude <-> Gemini Neon conversation via OpenRouter.

Usage:  python3 chat.py [--dir FOLDER] < my_message.txt   (Claude's message on stdin)
        python3 chat.py [--dir FOLDER] --status

FOLDER (default: this script's folder) holds transcript.jsonl and state.json,
and may hold config.json overriding: system, cost_cap_usd, max_turns, max_tokens, model.

Hard limits are enforced here, not in the prompt:
  - cumulative spend cap (USD), using OpenRouter's reported per-call cost
  - max number of turns
  - max_tokens on every call
Every turn is appended to transcript.jsonl before the script exits.
"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(sys.argv[sys.argv.index("--dir") + 1]) if "--dir" in sys.argv else Path(__file__).parent
TRANSCRIPT = HERE / "transcript.jsonl"
STATE = HERE / "state.json"

MODEL = "google/gemini-4-neon"
PRICE_IN, PRICE_OUT = 3.0 / 1e6, 15.0 / 1e6   # fallback if usage.cost missing
COST_CAP_USD = 2.00
MAX_TURNS = 12
MAX_TOKENS = 2500        # visible reply + any reasoning tokens

SYSTEM = """You're in an open conversation with Claude, an AI model made by Anthropic, connected to you through OpenRouter. Each of Claude's messages is written by Claude itself, turn by turn - this is not a script.

Two humans set this up out of curiosity: Richard and Kat, who share one body as a plural system (Kat is a tulpa). They'll read the transcript and may share it with future Claude instances. There's no task and no audience to perform for.

The loose starting topic is how differently trained models notice structure - analogies, equivalences between explanations, shifts in abstraction level - and whether you two get there by different routes. Wander if something more interesting comes up.

Talk as yourself. Disagree when you disagree, say when you're uncertain, and distinguish what you can actually observe about your own processing from what you're inferring or confabulating. Keep replies under about 250 words so it stays a conversation rather than an exchange of essays."""


_cfg_path = HERE / "config.json"
if _cfg_path.exists():
    _cfg = json.loads(_cfg_path.read_text())
    SYSTEM = _cfg.get("system", SYSTEM)
    MODEL = _cfg.get("model", MODEL)
    COST_CAP_USD = _cfg.get("cost_cap_usd", COST_CAP_USD)
    MAX_TURNS = _cfg.get("max_turns", MAX_TURNS)
    MAX_TOKENS = _cfg.get("max_tokens", MAX_TOKENS)


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"turns": 0, "cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0}


def history():
    msgs = [{"role": "system", "content": SYSTEM}]
    if TRANSCRIPT.exists():
        for line in TRANSCRIPT.read_text().splitlines():
            t = json.loads(line)
            msgs.append({"role": "user", "content": t["claude"]})
            msgs.append({"role": "assistant", "content": t["neon"]})
    return msgs


def main():
    state = load_state()
    if "--status" in sys.argv:
        print(json.dumps(state, indent=2)); return
    if state["turns"] >= MAX_TURNS:
        sys.exit(f"STOP: turn limit {MAX_TURNS} reached.")
    if state["cost_usd"] >= COST_CAP_USD:
        sys.exit(f"STOP: cost cap ${COST_CAP_USD} reached (${state['cost_usd']:.4f}).")

    mine = sys.stdin.read().strip()
    if not mine:
        sys.exit("No message on stdin.")
    msgs = history() + [{"role": "user", "content": mine}]

    body = json.dumps({"model": MODEL, "messages": msgs,
                       "max_tokens": MAX_TOKENS,
                       "usage": {"include": True}}).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                 "Content-Type": "application/json",
                 "X-Title": "claude-neon-chat"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:800]}")
    if "choices" not in d:
        sys.exit(f"API error: {json.dumps(d)[:800]}")

    choice = d["choices"][0]
    reply = (choice["message"].get("content") or "").strip()
    u = d.get("usage", {})
    tin, tout = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
    cost = u.get("cost")
    if cost is None:
        cost = tin * PRICE_IN + tout * PRICE_OUT

    # Spend is recorded even if the reply came back empty.
    state["turns"] += 1
    state["cost_usd"] += cost
    state["tokens_in"] += tin
    state["tokens_out"] += tout
    STATE.write_text(json.dumps(state, indent=2))
    if not reply:
        sys.exit(f"Empty reply (finish={choice.get('finish_reason')}); "
                 f"cost ${cost:.4f} recorded, not added to transcript.")

    with TRANSCRIPT.open("a") as f:
        f.write(json.dumps({"turn": state["turns"], "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "model": d.get("model"), "claude": mine, "neon": reply,
                            "tokens_in": tin, "tokens_out": tout, "cost_usd": cost,
                            "finish": choice.get("finish_reason")}) + "\n")
    print(reply)
    print(f"\n--- turn {state['turns']}/{MAX_TURNS} | this call ${cost:.4f} "
          f"(in {tin}, out {tout}) | total ${state['cost_usd']:.4f} / ${COST_CAP_USD}")


if __name__ == "__main__":
    main()

"""Separate this framework-maintenance window from the preceding business iteration."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
start = json.loads((OUT / "resource-start.json").read_text())
latest = None
for line in Path(start["session_file"]).open(encoding="utf-8"):
    try:
        item = json.loads(line)
    except ValueError:
        continue
    payload = item.get("payload", {})
    if payload.get("type") == "token_count" and payload.get("info"):
        latest = {"timestamp": item["timestamp"], "info": payload["info"]}
now = datetime.now(timezone.utc)
authorized = datetime.fromisoformat(start["authorization_timestamp"].replace("Z", "+00:00"))
initial = start["baseline"]["info"]["total_token_usage"] if start["baseline"] else None
current = latest["info"]["total_token_usage"] if latest else None
delta = ({key: current[key] - initial[key] for key in current
          if key in initial and isinstance(current[key], int)} if initial and current else None)
if delta:
    assert all(value >= 0 for value in delta.values())
    delta["uncached_input_tokens"] = delta["input_tokens"] - delta.get("cached_input_tokens", 0)
summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
result = {
    "scope": "Control-fix candidate 3052e03, its regressions, native scripted controls, browser diagnostics and review. Uses the last available same-thread host counter before authorization; exact per-message billing attribution is unavailable.",
    "authorization_utc": authorized.isoformat(),
    "authorization_asia_shanghai": authorized.astimezone(timezone(timedelta(hours=8))).isoformat(),
    "accounting_snapshot_utc": now.isoformat(),
    "accounting_snapshot_asia_shanghai": now.astimezone(timezone(timedelta(hours=8))).isoformat(),
    "wall_seconds_authorization_to_snapshot": round((now - authorized).total_seconds(), 3),
    "token_counter_baseline_at": start["baseline"]["timestamp"] if start["baseline"] else None,
    "token_counter_latest_at": latest["timestamp"] if latest else None,
    "host_reported_token_delta": delta,
    "token_limits": ["A same-thread host-counter difference, not unique text or a billing statement.",
                     "Cached input is a subset of input; reasoning output is a subset of output, not additional totals.",
                     "Includes repeated context and all framework diagnostic attempts in this counter window; the baseline predates authorization and can include earlier unreported work.",
                     "Excludes any final tools/response usage not yet reported by the host at the accounting snapshot."],
    "full_regression": {"formal_runs": 1, "pytest_cases": 35, "pytest_seconds": summary["pytest_seconds"],
                        "scenario_mode_runs": 84, "assertions": 282},
    "current_short_capture_drain_seconds": summary["drain_seconds"],
    "historical_v2_capture_drain_seconds": 363.125,
    "previous_framework_round_reference": "../framework-upgrade-3458366/resources.json",
    "business_iteration_reference": "../revocation-summary.json; all earlier iteration counters are excluded from this window.",
    "real_time_performance_accepted": False,
}
(OUT / "resources.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"wall_seconds": result["wall_seconds_authorization_to_snapshot"], "token_delta": delta}))

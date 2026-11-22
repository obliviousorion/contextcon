"""Demo script for the chaos harness: issues 3 sandbox actions, each with a slow send."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.platform import actions  # noqa: E402

for i in range(3):
    k = f"demo-{i}"
    actions.approve(k)
    actions.execute_approved(k, "send_evidence_request", f"vendor{i}.example",
                             lambda k=k: (time.sleep(0.3), actions.sandbox_send({"idempotency_key": k})))

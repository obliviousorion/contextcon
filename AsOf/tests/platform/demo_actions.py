"""Demo script for the chaos harness: issues 3 sandbox actions, each with a slow send."""
import time
from backend.platform import actions

for i in range(3):
    k = f"demo-{i}"
    actions.approve(k)
    actions.execute_approved(k, "send_evidence_request", f"vendor{i}.example",
                             lambda i=i: (time.sleep(0.3), actions.sandbox_send({"key": f"demo-{i}"})))

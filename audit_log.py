from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
AUDIT_LOG = ROOT / "logs" / "audit.log"


def audit_event(
    *,
    actor: str,
    event: str,
    action: str = "-",
    path: str = "-",
    decision: str = "-",
    outcome: str = "-",
    request_id: str = "-",
    mode: str = "-",
    **fields,
):
    timestamp = datetime.now(timezone.utc).isoformat()
    parts = [
        timestamp,
        f"actor={actor}",
        f"event={event}",
        f"mode={mode}",
        f"action={action}",
        f"path={path}",
        f"decision={decision}",
        f"outcome={outcome}",
        f"request_id={request_id}",
    ]

    for key, value in fields.items():
        parts.append(f"{key}={value}")

    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a") as f:
        f.write(" | ".join(parts) + "\n")

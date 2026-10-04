from pathlib import Path
import json

from policy_demo import authorize
from approval_store import (
    request_approval,
    get_request,
    consume_approval,
)
from audit_log import audit_event

ROOT = Path(__file__).parent

MODE = "enforce"


def audit(action: str, path: str, decision: str, outcome: str, request_id: str = "-"):
    audit_event(
        actor="guarded-ops",
        event="policy-enforcement",
        mode=MODE,
        action=action,
        path=path,
        decision=decision,
        outcome=outcome,
        request_id=request_id,
    )


def audit_execution(action: str, path: str, decision: str, request_id: str = "-"):
    audit_event(
        actor="guarded-ops",
        event="operation-execution",
        mode=MODE,
        action=action,
        path=path,
        decision=decision,
        outcome="executed",
        request_id=request_id,
    )


def audit_consumed(action: str, path: str, decision: str, request_id: str):
    audit_event(
        actor="guarded-ops",
        event="approval-consumed",
        mode=MODE,
        action=action,
        path=path,
        decision=decision,
        outcome="consumed",
        request_id=request_id,
    )


def handle_decision(action: str, path: str, request_id: str) -> bool:
    decision = authorize(path)
    print(f"[policy] {path} -> {decision}")

    if MODE == "observe":
        print(f"[observe] would-{decision.lower()}")
        audit(action, path, decision, f"would-{decision.lower()}", request_id)
        return True

    if decision == "DENY":
        audit(action, path, decision, "blocked", request_id)
        print("[blocked] action was not executed")
        return False

    if decision == "ASK":
        request = get_request(request_id)

        if request is None:
            request_approval(request_id, action, path)
            audit(action, path, decision, "pending-approval", request_id)
            print(f"[pending] human approval required: request_id={request_id}")
            return False

        status = request["status"]

        if status == "PENDING":
            audit(action, path, decision, "pending-approval", request_id)
            print(f"[pending] human approval required: request_id={request_id}")
            return False

        if status == "APPROVED":
            audit(action, path, decision, "approved", request_id)
            print(f"[approved] request_id={request_id}")
            return True

        if status == "DENIED":
            audit(action, path, decision, "denied", request_id)
            print(f"[denied] request_id={request_id}")
            return False

        if status == "CONSUMED":
            audit(action, path, decision, "replay-rejected", request_id)
            print(f"[rejected] request_id={request_id} was already consumed")
            return False

    return True


def guarded_read(path: str, request_id: str = "read-001"):
    if not handle_decision("read", path, request_id):
        return

    target = ROOT / path
    print(target.read_text())

    if MODE == "enforce":
        audit_execution("read", path, authorize(path), request_id)


def guarded_update_mock_prod(request_id: str = "prod-update-001"):
    path = "mock_prod/config.json"

    if not handle_decision("update", path, request_id):
        return

    target = ROOT / path
    data = json.loads(target.read_text())
    data["feature_flag"] = True
    target.write_text(json.dumps(data, indent=2))
    decision = authorize(path)
    audit_execution("update", path, decision, request_id)
    consume_approval(request_id)
    audit_consumed("update", path, decision, request_id)
    print("[executed] mock production config updated")


if __name__ == "__main__":
    print(f"Guarded operations ready. MODE={MODE}")

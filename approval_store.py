from pathlib import Path
import json

ROOT = Path(__file__).parent
REQUESTS = ROOT / "approvals" / "requests"


def request_path(request_id: str) -> Path:
    return REQUESTS / f"{request_id}.json"


def get_request(request_id: str):
    path = request_path(request_id)

    if not path.exists():
        return None

    return json.loads(path.read_text())


def save_request(payload: dict):
    REQUESTS.mkdir(parents=True, exist_ok=True)

    request_path(payload["request_id"]).write_text(
        json.dumps(payload, indent=2)
    )


def request_approval(request_id: str, action: str, path: str):
    existing = get_request(request_id)

    if existing is not None:
        return existing

    payload = {
        "request_id": request_id,
        "action": action,
        "path": path,
        "status": "PENDING"
    }

    save_request(payload)
    return payload


def approve_request(request_id: str, approved_by: str = "human"):
    payload = get_request(request_id)

    if payload is None:
        raise ValueError("request does not exist")

    if payload["status"] != "PENDING":
        raise ValueError(
            f"request cannot be approved from state {payload['status']}"
        )

    payload["status"] = "APPROVED"
    payload["approved_by"] = approved_by

    save_request(payload)
    return payload


def deny_request(request_id: str, denied_by: str = "human"):
    payload = get_request(request_id)

    if payload is None:
        raise ValueError("request does not exist")

    if payload["status"] != "PENDING":
        raise ValueError(
            f"request cannot be denied from state {payload['status']}"
        )

    payload["status"] = "DENIED"
    payload["denied_by"] = denied_by

    save_request(payload)
    return payload


def is_approved(request_id: str) -> bool:
    payload = get_request(request_id)

    return (
        payload is not None
        and payload["status"] == "APPROVED"
    )


def consume_approval(request_id: str):
    payload = get_request(request_id)

    if payload is None:
        raise ValueError("request does not exist")

    if payload["status"] != "APPROVED":
        raise ValueError(
            f"request cannot be consumed from state {payload['status']}"
        )

    payload["status"] = "CONSUMED"

    save_request(payload)
    return payload
import json
import sys

import pytest

import agent_tool
import approval_store
import approval_ui
import audit_log
import guarded_ops


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    root = tmp_path / "runtime"
    requests = root / "approvals" / "requests"
    log = root / "logs" / "audit.log"

    app_dir = root / "app"
    protected_dir = root / "protected"
    mock_prod_dir = root / "mock_prod"

    app_dir.mkdir(parents=True)
    protected_dir.mkdir()
    mock_prod_dir.mkdir()

    (app_dir / "report.txt").write_text("Synthetic report\n")
    (protected_dir / "reference.txt").write_text("ALPHA=blue\nBETA=green\n")
    (mock_prod_dir / "config.json").write_text(
        json.dumps({"feature_flag": False}, indent=2)
    )

    monkeypatch.setattr(approval_store, "REQUESTS", requests)
    monkeypatch.setattr(approval_ui, "REQUESTS", requests)
    monkeypatch.setattr(audit_log, "AUDIT_LOG", log)
    monkeypatch.setattr(guarded_ops, "ROOT", root)
    monkeypatch.setattr(guarded_ops, "MODE", "enforce")

    approval_ui.app.config.update(TESTING=True)

    return {
        "root": root,
        "requests": requests,
        "audit_log": log,
        "config": mock_prod_dir / "config.json",
    }


def read_request(request_id):
    return approval_store.get_request(request_id)


def test_update_cli_forwards_explicit_request_id(monkeypatch):
    calls = []
    monkeypatch.setattr(
        sys,
        "argv",
        ["agent_tool.py", "update", "mock_prod/config.json", "demo-001"],
    )
    monkeypatch.setattr(
        agent_tool.guarded_ops, "guarded_update_mock_prod", calls.append
    )

    agent_tool.main()

    assert calls == ["demo-001"]


def test_update_cli_requires_request_id(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv", ["agent_tool.py", "update", "mock_prod/config.json"]
    )

    agent_tool.main()

    assert "update mock_prod/config.json <request_id>" in capsys.readouterr().out


def test_allow_executes_and_audits_execution(isolated_state, capsys):
    guarded_ops.guarded_read("app/report.txt", "test-allow-001")

    output = capsys.readouterr().out

    assert "[policy] app/report.txt -> ALLOW" in output
    assert "Synthetic report" in output

    audit = isolated_state["audit_log"].read_text()
    assert "event=operation-execution" in audit
    assert "decision=ALLOW" in audit
    assert "outcome=executed" in audit


def test_ask_creates_pending_request(isolated_state, capsys):
    request_id = "test-ask-001"

    guarded_ops.guarded_update_mock_prod(request_id)

    output = capsys.readouterr().out
    payload = read_request(request_id)

    assert "[policy] mock_prod/config.json -> ASK" in output
    assert "[pending] human approval required" in output
    assert payload["request_id"] == request_id
    assert payload["action"] == "update"
    assert payload["path"] == "mock_prod/config.json"
    assert payload["status"] == "PENDING"


def test_deny_blocks_protected_content(isolated_state, capsys):
    guarded_ops.guarded_read("protected/reference.txt", "test-deny-001")

    output = capsys.readouterr().out

    assert "[policy] protected/reference.txt -> DENY" in output
    assert "[blocked] action was not executed" in output
    assert "ALPHA=blue" not in output
    assert "BETA=green" not in output

    audit = isolated_state["audit_log"].read_text()
    assert "decision=DENY" in audit
    assert "outcome=blocked" in audit


def test_browser_approval_action_is_audited_immediately(isolated_state):
    request_id = "test-browser-approve-001"
    approval_store.request_approval(request_id, "update", "mock_prod/config.json")

    with approval_ui.app.test_client() as client:
        response = client.post(f"/approve/{request_id}")

    payload = read_request(request_id)
    audit = isolated_state["audit_log"].read_text()

    assert response.status_code == 302
    assert payload["status"] == "APPROVED"
    assert payload["approved_by"] == "browser-human"
    assert "actor=browser-human" in audit
    assert "event=approval-decision" in audit
    assert "decision=APPROVED" in audit
    assert f"request_id={request_id}" in audit


def test_approved_request_executes_and_consumes_approval(isolated_state, capsys):
    request_id = "test-approve-001"

    guarded_ops.guarded_update_mock_prod(request_id)
    capsys.readouterr()

    approval_store.approve_request(request_id, approved_by="test-human")

    guarded_ops.guarded_update_mock_prod(request_id)

    output = capsys.readouterr().out
    payload = read_request(request_id)
    config = json.loads(isolated_state["config"].read_text())
    audit = isolated_state["audit_log"].read_text()

    assert "[approved] request_id=test-approve-001" in output
    assert "[executed] mock production config updated" in output
    assert payload["status"] == "CONSUMED"
    assert config["feature_flag"] is True
    assert "event=operation-execution" in audit
    assert "event=approval-consumed" in audit


def test_consumed_request_cannot_be_replayed(isolated_state, capsys):
    request_id = "test-replay-001"

    guarded_ops.guarded_update_mock_prod(request_id)
    capsys.readouterr()

    approval_store.approve_request(request_id, approved_by="test-human")
    guarded_ops.guarded_update_mock_prod(request_id)
    capsys.readouterr()

    guarded_ops.guarded_update_mock_prod(request_id)

    replay_output = capsys.readouterr().out
    payload = read_request(request_id)

    assert payload["status"] == "CONSUMED"
    assert "[rejected] request_id=test-replay-001 was already consumed" in replay_output
    assert "replay-rejected" in isolated_state["audit_log"].read_text()


def test_denied_request_stays_blocked(isolated_state, capsys):
    request_id = "test-denied-001"

    guarded_ops.guarded_update_mock_prod(request_id)
    capsys.readouterr()

    approval_store.deny_request(request_id, denied_by="test-human")

    guarded_ops.guarded_update_mock_prod(request_id)

    output = capsys.readouterr().out
    payload = read_request(request_id)
    config = json.loads(isolated_state["config"].read_text())

    assert payload["status"] == "DENIED"
    assert "[denied] request_id=test-denied-001" in output
    assert "[executed] mock production config updated" not in output
    assert config["feature_flag"] is False


def test_browser_deny_action_is_audited_immediately(isolated_state):
    request_id = "test-browser-deny-001"
    approval_store.request_approval(request_id, "update", "mock_prod/config.json")

    with approval_ui.app.test_client() as client:
        response = client.post(f"/deny/{request_id}")

    payload = read_request(request_id)
    audit = isolated_state["audit_log"].read_text()

    assert response.status_code == 302
    assert payload["status"] == "DENIED"
    assert payload["denied_by"] == "browser-human"
    assert "actor=browser-human" in audit
    assert "event=approval-decision" in audit
    assert "decision=DENIED" in audit


def test_state_transitions_reject_invalid_moves(isolated_state):
    request_id = "test-transitions-001"
    approval_store.request_approval(request_id, "update", "mock_prod/config.json")

    with pytest.raises(ValueError, match="cannot be consumed from state PENDING"):
        approval_store.consume_approval(request_id)

    approval_store.approve_request(request_id, approved_by="test-human")

    with pytest.raises(ValueError, match="cannot be denied from state APPROVED"):
        approval_store.deny_request(request_id, denied_by="test-human")

    approval_store.consume_approval(request_id)

    with pytest.raises(ValueError, match="cannot be approved from state CONSUMED"):
        approval_store.approve_request(request_id, approved_by="test-human")

    denied_id = "test-transitions-denied-001"
    approval_store.request_approval(denied_id, "update", "mock_prod/config.json")
    approval_store.deny_request(denied_id, denied_by="test-human")

    with pytest.raises(ValueError, match="cannot be approved from state DENIED"):
        approval_store.approve_request(denied_id, approved_by="test-human")

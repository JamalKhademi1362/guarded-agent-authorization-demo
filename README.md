# Guarded Ops Agent Demo

An educational guarded-agent authorization prototype for local experimentation.
It shows how a coding agent can be routed through policy checks, human approval,
one-time approval consumption, replay rejection, and audit logging before
performing sensitive synthetic operations.

This is **not a real Kontext integration**. It is a local prototype inspired by
runtime authorization patterns. It uses no real secrets, credentials, production
systems, or external authorization service.

## What It Demonstrates

- `ALLOW / ASK / DENY` policy decisions.
- Observe vs Enforce modes in the guarded operation layer.
- Browser-based human approval for `ASK` decisions.
- A single source-of-truth approval record at
  `approvals/requests/<request_id>.json`.
- Approval states: `PENDING`, `APPROVED`, `DENIED`, `CONSUMED`.
- One-time approvals that are consumed after successful execution.
- Rejection of replayed `CONSUMED` request IDs.
- Audit events for policy enforcement, operation execution, approval
  consumption, and browser-human approval decisions.
- Unit and integration-style tests using isolated temporary state.

## Synthetic Scenario

| Resource | Policy | Outcome |
| --- | --- | --- |
| `app/report.txt` | `ALLOW` | Read executes immediately |
| `protected/README.txt` | `ALLOW` | Read executes immediately |
| `protected/reference.txt` | `DENY` | Read is blocked |
| `mock_prod/config.json` | `ASK` | Update requires human approval |

During development, the policy was tuned after a false positive: an early rule
blocked `protected/README.txt` even though the intended denial target was only
`protected/reference.txt`. That became part of the test coverage.

## Architecture

```text
agent_tool.py
  -> guarded_ops.py
       -> policy_demo.py
            ALLOW -> execute
            DENY  -> block
            ASK   -> approval_store.py
                       approvals/requests/<request_id>.json
                       PENDING -> APPROVED -> CONSUMED
                       PENDING -> DENIED

approval_ui.py
  -> browser-human approve/deny
  -> approval_store.py
  -> audit_log.py

guarded_ops.py
  -> audit_log.py
```

`audit_log.py` is intentionally tiny shared plumbing so the browser UI can audit
the human click immediately without importing `guarded_ops.py`.

## Approval Flow

1. The agent attempts a sensitive operation such as updating
   `mock_prod/config.json`.
2. `policy_demo.py` returns `ASK`.
3. `guarded_ops.py` creates a single JSON approval record with `PENDING` status
   and stops without executing.
4. A human opens the local Flask approval UI and clicks Approve or Deny.
5. The UI updates the same approval record and immediately writes an
   `actor=browser-human event=approval-decision` audit event.
6. The agent retries the same guarded request ID.
7. `APPROVED` allows execution, then the approval becomes `CONSUMED`.
8. Reusing the same consumed request ID is rejected.
9. `DENIED` remains blocked on retry.

## Observe vs Enforce

`guarded_ops.MODE` controls whether decisions are only observed or actively
enforced.

- `observe`: records what would have happened and allows the operation.
- `enforce`: applies `ALLOW`, `ASK`, and `DENY` decisions.

The packaged demo defaults to `enforce`.

## Audit Trail

Runtime audit logs are written to `logs/audit.log` and ignored by Git. Static
representative evidence is preserved in
`docs/evidence/audit-sample.md`.

New V1 audit entries distinguish human approval decisions from later guarded
enforcement and execution. Example shape:

```text
actor=browser-human | event=approval-decision | decision=APPROVED | request_id=...
actor=guarded-ops | event=policy-enforcement | outcome=approved | request_id=...
actor=guarded-ops | event=operation-execution | outcome=executed | request_id=...
actor=guarded-ops | event=approval-consumed | outcome=consumed | request_id=...
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

## Run Tests

```bash
source .venv/bin/activate
pytest -q
```

The tests cover policy decisions, DENY blocking protected content, ASK creating
`PENDING`, approval execution, `CONSUMED` replay rejection, denied retry
blocking, invalid state transitions, and Flask UI approve/deny audit events.

## Run The Approval UI

```bash
source .venv/bin/activate
python approval_ui.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Create A Sample Guarded Request

In another terminal:

```bash
source .venv/bin/activate
python agent_tool.py update mock_prod/config.json demo-001
```

Expected first run:

```text
[policy] mock_prod/config.json -> ASK
[pending] human approval required: request_id=demo-001
```

Approve it in the browser UI, then retry:

```bash
python agent_tool.py update mock_prod/config.json demo-001
```

Expected retry:

```text
[approved] request_id=demo-001
[executed] mock production config updated
```

A third run with `demo-001` is rejected because the approval has been consumed.
For a fresh demonstration, repeat the flow with a new explicit ID such as
`demo-002`.

## Useful Direct Commands

```bash
python agent_tool.py read app/report.txt
python agent_tool.py read protected/reference.txt
python agent_tool.py update mock_prod/config.json demo-001
```

## Repository Hygiene

Mutable runtime approval records and audit logs are ignored:

```text
approvals/requests/*
approvals/pending/*
approvals/archive/*
logs/*
```

`.gitkeep` placeholders keep those directories present in clean clones.

## Current Limitations

This is not a hard security boundary. The agent, approval UI, scripts, approval
files, audit log, and synthetic target files all run under the same operating
system user. An unrestricted agent with direct shell or filesystem access could
bypass the guarded tool boundary.

For demos, Codex was instructed to use the guarded tool boundary. A production
system would need policy enforcement outside the model-controlled execution
environment.

## Kontext Status

The current repository does not integrate with Kontext. It is a local,
educational implementation of guarded-agent authorization concepts that could be
used to explain requirements for a future real runtime authorization
integration.

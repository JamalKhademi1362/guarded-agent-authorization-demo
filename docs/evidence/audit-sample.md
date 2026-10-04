# Static Audit Evidence Sample

This file preserves selected, sanitized project evidence from the local runtime
state that existed before packaging V1. It is static documentation, not a live
mutable audit log.

The lines below were selected from `logs/audit.log` and the single-record
approval files in `approvals/requests/`. They demonstrate the representative
flows used to validate the prototype.

## PENDING -> APPROVED -> EXECUTED

```text
2026-10-04T07:36:40.072255+00:00 | mode=enforce | action=update | path=mock_prod/config.json | decision=ASK | outcome=pending-approval | request_id=prod-update-004
2026-10-04T07:37:33.941613+00:00 | mode=enforce | action=update | path=mock_prod/config.json | decision=ASK | outcome=approved | request_id=prod-update-004
2026-10-04T07:37:33.950233+00:00 | mode=enforce | action=update | path=mock_prod/config.json | decision=ASK | outcome=executed | request_id=prod-update-004
```

## APPROVED -> EXECUTED -> CONSUMED

Approval record observed after successful execution:

```json
{
  "request_id": "prod-update-004",
  "action": "update",
  "path": "mock_prod/config.json",
  "status": "CONSUMED",
  "approved_by": "human"
}
```

V1 now also emits a separate `event=approval-consumed` audit line at consume
time for newly generated runs.

## Replay -> REJECTED

```text
2026-10-04T07:38:35.910279+00:00 | mode=enforce | action=update | path=mock_prod/config.json | decision=ASK | outcome=replay-rejected | request_id=prod-update-004
```

## PENDING -> DENIED

```text
2026-10-04T10:55:22.691860+00:00 | mode=enforce | action=update | path=mock_prod/config.json | decision=ASK | outcome=pending-approval | request_id=prod-update-006
2026-10-04T10:55:50.967652+00:00 | mode=enforce | action=update | path=mock_prod/config.json | decision=ASK | outcome=denied | request_id=prod-update-006
```

Approval record observed after denial:

```json
{
  "request_id": "prod-update-006",
  "action": "update",
  "path": "mock_prod/config.json",
  "status": "DENIED",
  "denied_by": "browser-human"
}
```

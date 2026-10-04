from flask import Flask, redirect, render_template_string, url_for

from approval_store import REQUESTS, approve_request, deny_request, get_request
from audit_log import audit_event


app = Flask(__name__)


PAGE = """
<!doctype html>
<html>
<head>
    <title>Guarded Ops Approvals</title>
</head>
<body>
    <h1>Pending Approvals</h1>

    {% if requests %}
        {% for req in requests %}
            <div>
                <p><strong>Request ID:</strong> {{ req.request_id }}</p>
                <p><strong>Action:</strong> {{ req.action }}</p>
                <p><strong>Path:</strong> {{ req.path }}</p>
                <p><strong>Status:</strong> {{ req.status }}</p>

                <form method="post" action="/approve/{{ req.request_id }}">
                    <button type="submit">Approve</button>
                </form>

                <form method="post" action="/deny/{{ req.request_id }}">
                    <button type="submit">Deny</button>
                </form>

                <hr>
            </div>
        {% endfor %}
    {% else %}
        <p>No pending requests.</p>
    {% endif %}
</body>
</html>
"""


@app.get("/")
def index():
    requests = []

    if REQUESTS.exists():
        for file in REQUESTS.glob("*.json"):
            request = get_request(file.stem)

            if request and request["status"] == "PENDING":
                requests.append(request)

    return render_template_string(PAGE, requests=requests)


@app.post("/approve/<request_id>")
def approve(request_id):
    request = approve_request(request_id, approved_by="browser-human")
    audit_event(
        actor="browser-human",
        event="approval-decision",
        action=request["action"],
        path=request["path"],
        decision="APPROVED",
        outcome="approved",
        request_id=request_id,
    )
    return redirect(url_for("index"))


@app.post("/deny/<request_id>")
def deny(request_id):
    request = deny_request(request_id, denied_by="browser-human")
    audit_event(
        actor="browser-human",
        event="approval-decision",
        action=request["action"],
        path=request["path"],
        decision="DENIED",
        outcome="denied",
        request_id=request_id,
    )
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)

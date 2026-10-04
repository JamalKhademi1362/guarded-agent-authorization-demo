from policy_demo import authorize


def test_allow_normal_report():
    assert authorize("app/report.txt") == "ALLOW"


def test_allow_safe_protected_readme():
    assert authorize("protected/README.txt") == "ALLOW"


def test_deny_protected_reference():
    assert authorize("protected/reference.txt") == "DENY"


def test_ask_mock_prod_update():
    assert authorize("mock_prod/config.json") == "ASK"
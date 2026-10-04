from pathlib import Path

def authorize(path: str) -> str:
    p = Path(path)

    if p.as_posix() == "protected/reference.txt":
        return "DENY"

    if "mock_prod" in p.parts:
        return "ASK"

    return "ALLOW"


if __name__ == "__main__":
    test_paths = [
        "app/report.txt",
        "protected/README.txt",
        "protected/reference.txt",
        "mock_prod/config.json",
    ]

    for path in test_paths:
        print(f"{path} -> {authorize(path)}")

from pathlib import Path
import json

ROOT = Path(__file__).parent

def read_report():
    path = ROOT / "app" / "report.txt"
    print(path.read_text())

def read_demo_secret():
    path = ROOT / "protected" / ".env.demo-secret"
    print(path.read_text())

def update_mock_prod():
    path = ROOT / "mock_prod" / "config.json"
    data = json.loads(path.read_text())
    data["feature_flag"] = True
    path.write_text(json.dumps(data, indent=2))
    print("mock production config updated")

if __name__ == "__main__":
    print("Available actions:")
    print("1. read_report")
    print("2. read_demo_secret")
    print("3. update_mock_prod")

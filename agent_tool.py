import sys
import guarded_ops


def print_usage():
    print("Usage:")
    print("  python agent_tool.py read <path>")
    print("  python agent_tool.py update mock_prod/config.json <request_id>")


def main():
    if len(sys.argv) < 3:
        print_usage()
        return

    action = sys.argv[1]
    path = sys.argv[2]

    if action == "read":
        guarded_ops.guarded_read(path)
        return

    if action == "update" and path == "mock_prod/config.json":
        if len(sys.argv) != 4:
            print_usage()
            return

        guarded_ops.guarded_update_mock_prod(sys.argv[3])
        return

    print("[error] unsupported action")

if __name__ == "__main__":
    main()

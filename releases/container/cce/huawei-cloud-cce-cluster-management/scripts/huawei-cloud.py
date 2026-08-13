#!/usr/bin/env python3
"""Huawei Cloud CCE Cluster Management — entry point.

Parses CLI key=value args (plus sandbox-injected --cli-* credential flags)
and dispatches to the modular dispatcher.
"""
import json
import os
import sys


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Missing action parameter"}))
        sys.exit(1)

    action = sys.argv[1]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from huawei_cloud.huawei_cloud_entry import parse_args
    from huawei_cloud.hcloud_runner import set_injected_credentials
    from huawei_cloud.dispatcher import dispatch_action, is_registered_action

    params, (ak, sk, token) = parse_args(sys.argv[2:])
    if ak or sk or token:
        set_injected_credentials(ak, sk, token)

    if not is_registered_action(action):
        print(json.dumps({"success": False, "error": f"Unknown action: {action}"}))
        sys.exit(1)

    result = dispatch_action(action, params)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

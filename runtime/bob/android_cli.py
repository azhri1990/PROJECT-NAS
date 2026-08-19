"""CLI entry point for the Android/Termux BOB worker."""
from __future__ import annotations

import argparse
import getpass
import sys
import time

from .android_activation import WorkerConfig, doctor, generate_worker_id, read_config, write_config
from .android_client import heartbeat, register, status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bob-worker")
    parser.add_argument("--state-dir", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--endpoint", required=True)
    init.add_argument("--token", default=None)
    init.add_argument("--worker-id", default=None)
    sub.add_parser("doctor")
    sub.add_parser("status")
    sub.add_parser("register")
    hb = sub.add_parser("heartbeat")
    hb.add_argument("--now", type=float, default=None)
    return parser


def _state(args):
    from pathlib import Path
    from .android_activation import DEFAULT_STATE_DIR
    return Path(args.state_dir).expanduser() if args.state_dir else DEFAULT_STATE_DIR


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state_dir = _state(args)
    if args.command == "init":
        token = args.token or getpass.getpass("BOB worker token: ")
        config = WorkerConfig(args.worker_id or generate_worker_id(), args.endpoint, token)
        path = write_config(config, state_dir)
        print(f"configured worker {config.worker_id}")
        print(f"state: {path}")
        return 0
    if args.command == "doctor":
        result = doctor(state_dir)
        print(result)
        return 0 if result["ok"] else 1
    try:
        config = read_config(state_dir)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"worker is not configured: {exc}", file=sys.stderr)
        return 2
    if args.command == "register":
        result = register(config)
    elif args.command == "heartbeat":
        result = heartbeat(config, args.now if args.now is not None else time.time())
    else:
        result = status(config)
    print(result.payload if result.ok else result.error)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Load the canonical PROJECT-NAS AI operating prompt."""

import argparse
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULTS = [
    os.path.join(BASE_DIR, "ai", "MASTER_PROMPT.md"),
    os.path.join(BASE_DIR, "ai", "AI_OPERATING_SYSTEM_SUMMARY.md"),
]


def load_prompt():
    for path in DEFAULTS:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read(), path
    return "", None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", "-o", help="Write prompt to file instead of stdout")
    args = parser.parse_args()

    text, path = load_prompt()
    if not text:
        print("# No prompt found in ai/")
        raise SystemExit(1)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"Wrote prompt from {path} to {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()

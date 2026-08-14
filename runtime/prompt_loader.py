"""
Simple prompt loader for PROJECT-NAS.
Loads ai/MASTER_PROMPT.md if present, else falls back to ai/AI_OPERATING_SYSTEM_SUMMARY.md.
Writes the effective prompt to stdout or to a file for consumption by local agents.

Usage:
  python runtime/prompt_loader.py [--out PATH]

"""
import argparse
import os

DEFAULTS = [
    os.path.join('ai', 'MASTER_PROMPT.md'),
    os.path.join('ai', 'AI_OPERATING_SYSTEM_SUMMARY.md'),
]


def load_prompt():
    for p in DEFAULTS:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return f.read(), p
    return ("", None)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', '-o', help='Write prompt to file instead of stdout')
    args = p.parse_args()

    text, path = load_prompt()
    if not text:
        print('# No prompt found in ai/ — create ai/MASTER_PROMPT.md or ai/AI_OPERATING_SYSTEM_SUMMARY.md')
        return

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'Wrote prompt from {path} to {args.out}')
    else:
        print(text)

if __name__ == '__main__':
    main()

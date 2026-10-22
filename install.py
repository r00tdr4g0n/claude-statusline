#!/usr/bin/env python3
"""Install the Claude Code status line.

What it does:
  1. Copies statusline-command.py next to this file into ~/.claude/.
  2. Backs up ~/.claude/settings.json (to settings.json.bak) and sets its
     "statusLine" entry to run the copied script with this Python.

Run it with the same Python you want the status line to use:
    python install.py        (Windows)
    python3 install.py       (macOS / Linux)

It prints what it changed. Re-running is safe; it overwrites the script and
the statusLine entry and keeps the latest backup.
"""

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_NAME = "statusline-command.py"


def main():
    src = os.path.join(HERE, SCRIPT_NAME)
    if not os.path.isfile(src):
        sys.exit("not found next to installer: " + src)

    claude_dir = os.path.join(os.path.expanduser("~"), ".claude")
    os.makedirs(claude_dir, exist_ok=True)

    dest = os.path.join(claude_dir, SCRIPT_NAME)
    shutil.copyfile(src, dest)
    print("copied script -> " + dest)

    # Absolute paths make the command work regardless of PATH or ~ expansion.
    command = '"{}" "{}"'.format(os.path.abspath(sys.executable), dest)

    settings = os.path.join(claude_dir, "settings.json")
    data = {}
    if os.path.exists(settings):
        shutil.copyfile(settings, settings + ".bak")
        print("backed up settings -> " + settings + ".bak")
        try:
            with open(settings, encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            print("warning: settings.json was not valid JSON; starting fresh")
            data = {}

    data["statusLine"] = {"type": "command", "command": command}
    with open(settings, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)

    print("set statusLine -> " + command)
    print("Done. Restart Claude Code (or start a new session) to see it.")


if __name__ == "__main__":
    main()

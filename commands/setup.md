---
description: Install the gauge status line into this user's Claude Code settings
allowed-tools: Bash
---

Set up the gauge status line for this user by running the bundled installer:

```
python "${CLAUDE_PLUGIN_ROOT}/install.py"
```

(If `python` is not found, use `python3`.)

The installer copies `statusline-command.py` into `~/.claude/`, backs up
`~/.claude/settings.json` to `settings.json.bak`, and sets its `statusLine`
entry to run the script. After it finishes, tell the user the status line is
configured and will appear after they restart Claude Code or start a new session.

# Qwen Code Agent

Local coding agent for LM Studio. It uses the already-installed `qwen2.5-coder-7b-instruct` model through the local API at `http://127.0.0.1:1234/v1`; it does not install or download models.

## Files

- `agent.py`: UI, conversation history, tools, and workspace access.
- `web_access.py`: public DuckDuckGo search and HTTP/HTTPS page reading.
- `askpass.py`: temporary Git authentication for reading private repositories through an existing `gh` login. The token stays in the process environment; it is not put in the URL or displayed.
- `icon.png`: application icon.
- `vendor/tkinterdnd2/`: drag-and-drop dependency (Linux x64 binary). Notices and license are under `vendor/`.
- `tests/`: local tests for plans, paths, approvals, backups, links, and web navigation.

## UI

The UI uses graphite with lavender accents, compact side navigation, a centered conversation column, and rounded user-message bubbles. Assistant responses avoid heavy cards; the input field is prominent and automatic scrolling follows the conversation.

The agent stores configuration, history, and memory in user-local directories outside this repository:

- `~/.local/share/lmstudio-qwen-agent/config.json`
- `~/.local/state/lmstudio-qwen-agent/projects/<id>/`: history, memory, plans, and backups of edited files.
- `~/.local/state/lmstudio-qwen-agent/backups/`: application-installation backups.

## Local installation

Copy `agent.py`, `web_access.py`, `askpass.py`, `icon.png`, and `vendor/tkinterdnd2/` to `~/.local/share/lmstudio-qwen-agent/`. Preserve an existing `config.json`. Then run `python3 ~/.local/share/lmstudio-qwen-agent/agent.py` or use a `.desktop` shortcut with that command.

Python 3 with system Tkinter is required. For private GitHub access, install `gh` and sign in locally with `gh auth login`. The agent only reads repository files supplied by the user; it does not create commits or push changes.

## Workflow

1. Inspect the request, `AGENTS.md` instructions, files, and Git state before proposing changes.
2. For multi-step tasks, show a short plan in the sidebar and update progress.
3. Show a diff and request approval before writing a file. A copy of the previous version is stored in the private workspace state.
4. Request approval for each command. Commands start in the workspace without a shell, but use the user's account permissions and may reach other files on the computer.
5. Keep conversations, memory, and archived plans separated by workspace. History and memory stay on the machine.

## Limits and privacy

- Listing, reading, searching, and editing tools are scoped to the selected workspace and reject symbolic links.
- The command executor is not an operating-system sandbox. Approve only commands you understand.
- GitHub reading clones temporarily into a temporary directory, without checkout or hook execution; Git reads files up to 256 KiB. Authentication depends on an existing `gh` login.
- Search sends terms to DuckDuckGo. Navigation accepts public HTTP/HTTPS pages and blocks local/private destinations, non-web schemes, and ports other than 80/443. Browser cookies and credentials are not sent.
- Edits are shown as diffs, but the model proposes final file contents instead of generating incremental patches.

## Tests

From the repository root:

```sh
python3 -m unittest discover -s tools/qwen-code-agent/tests -v
```

[Português](README.md) · [English](README.en.md)

# File sharing

Upload your own file, share it with a named user and cancel their access. The next download rechecks the current grant. The owner keeps access; a remaining recipient is unaffected.

This is the repaired application source used by the [VibeLens walkthrough](https://liblog.vip/VibeLens/demo.html?lang=en). Its native state and shared-rule executor run independently. The [review materials](../../docs/review/file-sharing-demo/README.md) contain complete observed-project source, recordings, failed and repaired runs, screenshots and the scripted development conversations.

## Run

Requires Python 3.10 or later. From this directory:

```bash
python -m venv .venv
# Windows: .venv/Scripts/python; macOS/Linux: .venv/bin/python
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python run.py
```

Open [the local application](http://127.0.0.1:8879/). Choose an account on its login page. All three demo passwords are `file-demo-2026`.

| Account | Name | Example role |
|---|---|---|
| `linzhou` | 林舟 | Upload and share |
| `xuning` | 许宁 | Receive and download |
| `zhoulan` | 周岚 | Check access without a grant |

Each user can upload and own their own files. Ownership and explicit recipient grants determine access to each file. The local example uses synthetic accounts and stores its SQLite file and session secret in ignored `data/`.

## Read the source

- `app/service.py`: upload, sharing, access and revocation behavior.
- `app/web.py`, `templates/`, `static/`: HTTP routes and the application interface.
- `app/models.py`, `app/storage.py`: relational schema and storage.
- `bo_stategraph/project.json`, `workflow.py`, `native_executor.py`: state declaration and actual transitions.
- `bo_stategraph/policy/`: shared rule execution, parameter bindings and current-source checks.

The recorded application and state/rule source files are retained byte for byte for traceability. The standalone launcher, short dependency list and this guide are added for running the core directly. To observe another iteration, install VibeLens in your working project and explicitly invoke `$vibelens`; the agent attaches observation and maintains the graph as you develop.

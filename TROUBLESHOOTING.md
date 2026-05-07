# Troubleshooting

## SQLite file looks unreadable in Excel/WPS
That is expected. A `.sqlite3` file is a database, not a spreadsheet.
Open the exported CSV for spreadsheet workflows.

## `ModuleNotFoundError: No module named src`
Rerun the notebook setup cell so project paths and dependencies are initialized.

## OQMD timeout or HTTP 502
Wait briefly, then rerun.
If the downloader safely stops, resume from the SQLite backup/checkpoint.

## GitHub PR has conflicts
Close the PR and create a fresh Codex task from current `main`.
Do not manually resolve long-lived stale branch conflicts.

## `export_all` fails because `fetch_all_rows` is missing
Use `scripts/export_from_sqlite.py` to export directly from the SQLite database.

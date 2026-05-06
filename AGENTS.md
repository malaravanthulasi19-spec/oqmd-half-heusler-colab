# Project instructions for Codex

This project runs in Google Colab.

## Main goal

Download OQMD formationenergy data for cubic half-Heusler materials using:

generic=ABC AND ntypes=3 AND spacegroup="F-43m" AND band_gap>0

Expected raw count is about 3117 entries.

## Rules

- Keep notebooks simple.
- Put real logic in src/ Python files.
- Use SQLite checkpointing.
- Store OQMD rows by entry_id as primary key.
- Use batch inserts with executemany.
- Prefer one global BASE_FILTER query first.
- Use element_set fallback only if the global query repeatedly fails.
- Do not use long disjoint filters with many NOT element clauses.
- Avoid long hidden retry loops.
- Use short visible retries and adaptive page sizes.
- Make every long-running process resumable.
- Use /content for active runtime files.
- Use Google Drive only for backups and exports.
- Do not hardcode local machine paths.
- Do not store secrets in code.

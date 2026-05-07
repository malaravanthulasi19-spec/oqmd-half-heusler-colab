# OQMD Half-Heusler Colab Downloader

Clean Google Colab project to download OQMD `formationenergy` data for cubic half-Heusler materials.

## Target filter

```text
generic=ABC AND ntypes=3 AND spacegroup="F-43m" AND band_gap>0
```

Known expected raw count is about **3117** entries.

## Project structure

- `notebooks/run_oqmd_downloader.ipynb`: Simple Colab orchestrator notebook.
- `src/`: Download, API, DB, and export logic.
- `tests/`: Minimal tests for SQLite resumability behavior.

## Colab usage

1. Open `notebooks/run_oqmd_downloader.ipynb` in Google Colab.
2. Run setup cell to clone your GitHub repo and install requirements.
3. Configure paths:
   - Active runtime files in `/content/oqmd_runtime`
   - Optional Google Drive folder only for backups/exports
4. Run download cell.
5. Run export cell to write CSV + Parquet.

## Resumability

- Uses SQLite checkpointing via `download_state.last_offset`.
- `entry_id` is the primary key; reruns are safe and idempotent.
- Adaptive page sizes and short visible retries are used for unstable network/API behavior.

## Security

- No secrets or API keys are stored in source code.
- Do not commit local credentials or Colab auth tokens.

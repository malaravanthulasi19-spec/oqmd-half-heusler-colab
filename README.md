# OQMD Half-Heusler Colab Downloader

Google Colab project to download OQMD `formationenergy` data for cubic half-Heusler materials.

## Target filter

`generic=ABC AND ntypes=3 AND spacegroup="F-43m" AND band_gap>0`

Expected raw count is about **3117**.

## Colab workflow (safe resume)

1. Open `notebooks/run_oqmd_downloader.ipynb`.
2. Setup cell clones repo into `/content/oqmd-half-heusler-colab`, enters it, adds repo to `sys.path`, and installs requirements.
3. Mount Google Drive for backup/export files only.
4. Optionally restore a prior SQLite backup from Drive.
5. Run downloader cell.
6. If OQMD is unstable (timeouts/502), progress is saved and it's **safe to rerun later**.
7. Export CSV + Parquet and backup DB/outputs to Drive.

## Design

- Notebook is orchestration only.
- Logic is in `src/`.
- SQLite checkpointing (`download_state` + `filter_progress`) supports resumable global and fallback modes.
- Data rows are keyed by `entry_id` primary key (idempotent upsert).
- Uses one global filter first, then fallback element queries when needed.
- Visible retries with adaptive limits and 502 cooldown.
- No secrets or API keys in source code.


## Notebook status

The status cell prints:
- row count
- last saved offset
- current mode and filter
- active database path

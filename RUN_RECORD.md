# Run Record

## Project
OQMD cubic half-Heusler downloader

## Filter
generic=ABC AND ntypes=3 AND spacegroup="F-43m" AND band_gap>0

## Expected count
about 3117

## Final result
- `unique_rows`: 3117
- completed fallback jobs: 81
- pending fallback jobs: 0

## Downloader result
`DownloadResult(total_inserted=11505, safe_stop=True)`

## Interpretation
`total_inserted` is larger than `unique_rows` because fallback jobs overlap.
The real final dataset size is `unique_rows=3117` because `entry_id` deduplicates rows.

## Colab export paths
- CSV: `/content/oqmd_runtime/exports/oqmd_half_heusler.csv`
- Parquet: `/content/oqmd_runtime/exports/oqmd_half_heusler.parquet`
- SQLite: `/content/oqmd_runtime/oqmd_half_heusler.sqlite3`

## Google Drive backup path
- SQLite: `/content/drive/MyDrive/oqmd_backups/oqmd_half_heusler.sqlite3`

## Recommended GitHub Release assets
- `oqmd_half_heusler.csv`
- `oqmd_half_heusler.parquet`
- `oqmd_half_heusler.sqlite3`
- `run_log.txt`

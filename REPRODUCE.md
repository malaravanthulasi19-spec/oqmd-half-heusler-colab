# Reproduce the OQMD Half-Heusler Colab Run

This is the simplest, exact workflow to reproduce the successful download.

1. Open this GitHub repository.
2. Make sure `main` is clean and up to date.
3. Start a **fresh Codex task** from `main`.
4. Do **not** continue old Codex tasks after merging.
5. If a PR has conflicts, close it instead of resolving manually.
6. Merge only clean PRs.
7. From GitHub `main`, open `notebooks/run_oqmd_downloader.ipynb` in Colab.
8. In Colab, click **Copy to Drive**.
9. Run cells one by one in this order:
   - Setup
   - Restore backup
   - Status
   - Downloader
   - Status
   - Export/backup
10. Never use **Run all** on first run.
11. If OQMD returns timeout or HTTP 502, let the downloader stop safely.
12. Resume from SQLite backup.
13. Use `unique_rows` as the final count (not `total_inserted`).
14. Export CSV and Parquet only after row count is greater than 0.
15. Store final files in GitHub Releases.

# Successful Codex Prompts

Use these prompts as reusable templates for future runs.

## 1) Reliable job-queue downloader prompt

Build or refine a resilient OQMD downloader for the filter:
`generic=ABC AND ntypes=3 AND spacegroup="F-43m" AND band_gap>0`.
Requirements:
- global BASE_FILTER first
- resumable SQLite checkpointing
- `entry_id` primary key dedup
- short visible retries, adaptive page size
- fallback job queue by `element_set` only after repeated global failures
- safe stop on repeated upstream errors (timeout/502)
- no long hidden retry loops

## 2) Export fix prompt

Fix export so CSV/Parquet can be produced directly from SQLite rows stored as `oqmd_rows.payload_json`.
Do not modify downloader behavior.
Provide a standalone script fallback for exports when notebook helper paths fail.

## 3) Documentation prompt

Create concise reproducibility docs for Colab operators, including run order, safe resume behavior,
count interpretation (`unique_rows` vs `total_inserted`), and release packaging.

## Rules for all Codex tasks

- Always start from current `main`.
- Do not reuse stale branches.
- Do not merge conflicted PRs.
- Do not use placeholders like `<your-user>`.

# CodePulse backend — analysis engine + FastAPI

This backend accepts coding-platform profile data, calculates combined analytics, and exposes them through FastAPI. It keeps profile-level ratings separate and uses canonical problem IDs for safe cross-profile deduplication.

## 1. Run on Windows / PowerShell

Open PowerShell in the folder containing `main.py`: 

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs`. Health check: `http://127.0.0.1:8000/health`.

## 2. API endpoint

`POST http://127.0.0.1:8000/api/v1/analysis`

The request body contains `display_name` and a `platforms` array. Each profile can include:

- `platform_name`, `username`, `current_rating`
- `total_solved`, `correct_submissions`, `failed_submissions`, `total_attempted`
- `topics`: legacy aggregate topic counts
- `problem_activity`: one record per distinct attempted problem, with `platform_problem_id`, `canonical_id`, `tags`, and `solved`
- `submission_activity`: one record per judged submission, with `submission_id`, `platform_problem_id`, `canonical_id`, `tags`, and `accepted`
- `contest_history`, `daily_activity`, and `data_complete` (whether the importer reached the end of available history)
- `pagination_pages`, `duplicate_submission_records`, `missing_submission_ids`, `problemset_lookup_misses`, and `problemset_entries_without_tags` (optional importer diagnostics)

For exact unique topic analytics, send `problem_activity` with canonical IDs and tags. For topic submission accuracy, send `submission_activity` with judged verdicts and tags. Missing information must remain missing; do not fabricate IDs, tags, verdicts, or completeness flags.

## 3. Metric definitions

- `overview.total_solved`: distinct solved canonical problem IDs known to the engine. If problem details are missing, the backend preserves reported totals but marks exact uniqueness unavailable.
- `duplicate_solved_across_profiles`: number of known solved problem IDs shared by multiple connected profiles. `duplicate_solved_across_platforms` remains as a backward-compatible legacy field name.
- Topic `solved` / `attempted`: unique canonical problems per topic. A multi-tag problem contributes once to each applicable topic.
- `completion_rate`: unique attempted problems eventually solved divided by unique attempted problems.
- `submission_success_rate`: accepted judged submissions divided by all accepted and failed judged submissions. Repeated attempts on one problem remain separate submission events.
- A submission with multiple tags contributes once to each tagged topic. Therefore topic submission totals overlap and should not be added together.
- Ratings are never combined across platforms because rating scales differ.
- Missing IDs/tags and partial imports are surfaced through `data_quality`.

Topic classifications are transparent heuristics based on submission acceptance rate and require at least 10 judged submissions: Strong (80%+), Good (65–79.99%), Developing (40–64.99%), Needs Improvement (below 40%); otherwise Insufficient Data. These labels are practice signals, not definitive measures of skill.

## 4. Test the engine

```powershell
python -m pytest -q
```

## 5. Test real Codeforces demo profiles

Run from the project root:

```powershell
python test_real_profiles.py
```

The importer fetches submission history in pages of up to 1,000 records and continues until Codeforces returns a short page. It waits between API requests and retries transient HTTP/API failures. This can take several minutes for profiles with large histories.

For a faster, intentionally partial test, set a cap before running:

```powershell
$env:CODEFORCES_MAX_SUBMISSIONS = "1000"
python test_real_profiles.py
Remove-Item Env:CODEFORCES_MAX_SUBMISSIONS
```

When a cap is reached, `data_complete` is false. With no cap, the importer marks the fetched submission history complete only after the API returns a short final page. The importer also records the number of pages fetched and detects repeated submission IDs across page boundaries. Repeated IDs are removed from analytics, while offsets still advance by the raw number of records returned by the API.

## 6. CORS

Default CORS origins include Vite (`localhost:5173`) and common React (`localhost:3000`) development addresses. Set `CORS_ORIGINS` to your frontend URL(s), separated by commas, if needed.

## 7. Project structure

```text
main.py
models/       # Pydantic input/output contracts
engine/       # normalization, aggregation, contest and recommendation logic
tests/        # automated tests
sample_data/  # sample API request
test_real_profiles.py  # paginated Codeforces demo importer
```

## 8. Input conventions the validators enforce

- Ratings may be fractional (LeetCode); they are rounded to whole numbers on input.
- `timestamp` is Unix **seconds**. Millisecond values are converted automatically; anything after 2100-01-01 is rejected with HTTP 422.
- `platform_problem_id` must not be blank. Optional text fields (`canonical_id`, `title`, `url`, `difficulty`, `submission_id`) become `null` when blank.
- Repeated `submission_id`s inside one profile count once. If the same ID appears with different verdicts, the accepted verdict wins.
- `overview.total_solved` never falls below the largest single-profile `total_solved`, even when some profiles send no problem-level records.
- `topic_analytics[].solved` is `null` (unknown) for topics that appear only in `submission_activity`.
- Profiles that send only legacy `topics` (no `problem_activity`) are added on top of the unique counts and flagged in `data_quality`.
- Output order is independent of the order profiles are sent in.

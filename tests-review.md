# Test Hardening Report

## Baseline
- `pytest -q` (without coverage opts) initially failed on Windows with `PermissionError` in `tests/unit/test_persist_db.py` because temporary files remained locked.
- Default `pytest` invocation crashed due to missing `pytest-cov`; commands depending on `-n/--count` were unavailable (xdist / pytest-repeat not installed).
- `pytest --durations=25` highlighted retry/vault scenarios as slowest (7.21s max). Failures identical to baseline above.

## Changes Implemented
1. **Windows-safe temp database handling**  
   Reworked `_EncryptedDatabaseContext` to use `tempfile.mkstemp` ensuring handles are closed before unlink, fixing persistent test failures.
2. **Deterministic execution**  
   Added session-level seeding (`PYTHONHASHSEED=0`, `random.seed(0)`) and rewrote retry tests to avoid wall-clock sleeps via monkeypatched jitter capture.
3. **Coverage & tooling**  
   Installed `pytest-cov`, restored default `addopts`, and enforced `--cov-fail-under=72` in `pyproject.toml`.  
4. **New / refined tests**  
   - Extended `tests/test_file_utils.py` with permission/error-path checks.  
   - Added `tests/unit/test_shortcuts.py` for CLI shortcut routing.  
   - Added `tests/unit/test_cli_main.py` for the `QueryProcCode` alias.  
   - Expanded `tests/unit/test_query_proc_code_template.py` to cover the CLI command delegation.  
   - Reworked retry suite for deterministic jitter validation.

## Results
- Full suite: **496 passed, 2 skipped** in 29.03s.  
- Coverage: **72.05 %** (↑ from 70.97 %). Notable gains:  
  - `utils/file_utils` → 91.04 % (was 47.76 %).  
  - `cli/shortcuts` → 51.43 % (was 45.71 %).  
  - Stable retry timings without real sleeps.
- Coverage gate now enforced at 72 % for CI/local runs.

## Outstanding / Follow-up
- CLI (`history_cmd`, `persist_cmd`, `vault_cmd`) still <60 % coverage—consider isolating heavy behaviour with injectable services for targeted unit tests.
- `pytest -n` / `--count` remain unavailable; install `pytest-xdist` / `pytest-repeat` if parallel or flake detection is required.
- Long-running vault/retry integration tests still dominate durations; future work could mock timers or split into `slow` marker.

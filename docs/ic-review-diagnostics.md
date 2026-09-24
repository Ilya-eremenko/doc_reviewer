# IC Review Internal Diagnostics

IC Review stores the last ten diagnostic records in
`analysis_check_runs.run_parameters.ic_review_error_diagnostics`. These records
are removed from all API responses, including admin responses. The public error
contract, analysis rules, provider calls, and existing fallback policy are unchanged.

Version 2 adds:

- `context`: analysis/document/check-run/step IDs, provider/model, skill ID/version,
  source snapshot ID/revision/fingerprint, and the operation being performed.
- `context.app_release_sha`: the actual worker image's release tag. Production
  Compose passes the deploy script's SHA-pinned `GATE_WORKER_IMAGE` as
  `APP_RELEASE_IMAGE`. Local or non-SHA-tagged images report `unknown`; this is
  never inferred from a developer's checkout or the current GitHub main branch.
- RQ job ID, retries remaining, and retry count when available. Unknown retry
  counts are omitted, not invented. These are queue retries, not model retries.
- Schema filename and SHA-256 of canonical schema JSON, identifying the exact
  runtime contract even when the schema has no explicit version number.
- Validation path, schema path, validator, expected size/type constraint, and
  actual type/length. Object keys not declared by the schema become `<dynamic>`.
  No actual values, enum contents, prompts, or rejected model output are logged.
- JSON line/column/position, HTTP error status/request ID when available, elapsed
  milliseconds, and nested exception details alongside existing safe DB metadata.
- For deterministic pipeline failures: script names/exit codes and validation
  failure count, without script arguments, stdout/stderr, or artifact paths.

Role errors are emitted as one `ic_review_diagnostic {JSON}` worker-log line
before database recovery. This makes the original failure observable even if
rollback, reload, or error persistence also fails. The same safe record is kept
in the database when it is writable. Plain RQ log formatting is sufficient;
no custom JSON formatter is required. A role and its outer job may each emit a
record for the same error; correlate them by check-run ID, not as two failed runs.

## Investigation

1. Obtain the analysis URL/ID and approximate failure time from the user.
2. Search worker logs for `ic_review_diagnostic` and that analysis ID. Check the
   release SHA first, then `operation`, `step_name`, schema hash, and validation
   path. For `minLength`, compare `expected` with `actual_length`.
3. With authorized server/DB access, read the persisted records (read-only SQL):

```sql
SELECT id, analysis_id, current_stage,
       run_parameters->'ic_review_error_diagnostics' AS diagnostics
FROM analysis_check_runs
WHERE analysis_id = '<analysis UUID>'
ORDER BY created_at DESC;
```

4. If there is no database record, use the worker log. If a worker was killed
   before Python handled the error, there may be neither; correlate deployment,
   process, and queue logs. This change does not add durable resume or heartbeat.

Historical version-1 records remain readable but cannot retroactively acquire
missing release/schema data. Do not re-run a user's analysis just to fill logs.
Request IDs may be absent when the adapter/provider did not return one. Logs
must never be augmented with document text, workbook values, provider keys,
raw model responses, SQL parameters, or full exception messages.

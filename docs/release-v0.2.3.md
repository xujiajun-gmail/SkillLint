# SkillLint v0.2.3 Release Notes

SkillLint v0.2.3 is a web hardening and deployment release. It improves input validation across CLI/Web/API, adds browser-side prechecks for the web UI, expands `skilllint-web` runtime configurability, and ships first-class deployment artifacts for Docker, Compose, and systemd.

## Highlights

### Stronger scan input validation

This release significantly strengthens pre-scan input handling for:

- local directories
- zip archives
- remote URLs

New validation coverage includes:

- skill root checks with `SKILL.md`
- maximum file-count enforcement
- single-file and total-size limits
- path depth / path length limits
- archive path traversal rejection
- archive symlink-entry rejection
- archive size validation
- remote download size validation
- redirect limit enforcement
- remote URL scheme / host / credential checks

The validation model is now documented in:

- `docs/skilllint-input-validation.md`

### Structured validation errors for API consumers

Input validation failures returned by the web/API layer are now structured and machine-readable.

Current error payload shape:

```json
{
  "detail": {
    "code": "missing_skill_entry",
    "message": "Input is not a skill package: no SKILL.md was found.",
    "metadata": {}
  }
}
```

This makes it easier for:

- the web frontend
- future external integrations
- automation pipelines

to react to stable error codes instead of parsing free-form text.

### Better web-side validation feedback

The SkillLint web app now performs browser-side prechecks before upload or remote scan submission.

Current prechecks cover:

- archive extension / size
- directory file count
- presence of `SKILL.md`
- per-file and total upload size
- path depth / path length
- unsafe or obviously local/private URL hosts
- embedded credentials in remote URLs

The frontend also renders clearer validation hints and maps structured backend error codes to more useful user-facing guidance.

### More configurable `skilllint-web` runtime

The `skilllint-web` launcher now supports:

- `--host`
- `--port`
- `--reload`
- `--workers`
- `--log-level`

Matching environment variables are also supported:

- `SKILLLINT_WEB_HOST`
- `SKILLLINT_WEB_PORT`
- `SKILLLINT_WEB_RELOAD`
- `SKILLLINT_WEB_WORKERS`
- `SKILLLINT_WEB_LOG_LEVEL`

Defaults:

- host: `127.0.0.1`
- port: `18110`
- reload: `false`
- workers: `1`
- log level: `info`

This release also enforces that `reload` cannot be combined with `workers > 1`.

### First deployment artifacts for the web app

The repository now includes deployable web runtime artifacts:

- `Dockerfile`
- `.dockerignore`
- `compose.yaml`
- `deploy/systemd/skilllint-web.service`

Deployment guidance is documented in:

- `docs/skilllint-web-deployment.md`

## Scope

v0.2.3 does not add a new scan engine or a new output format. It focuses on:

- safer and stricter scan input handling
- better web UX for invalid inputs
- better API ergonomics for validation errors
- more practical web deployment and runtime configuration

## Validation

- `ruff check src tests`
- `pytest -q`

Current validation result at release time:

- 93 tests passed

## Suggested next work

- add reverse-proxy-specific runtime options such as forwarded headers controls
- add CI workflow to validate lint, tests, and Docker build together
- expose validation limits and active runtime config through a health or info endpoint
- add production reverse proxy examples such as Nginx or Caddy

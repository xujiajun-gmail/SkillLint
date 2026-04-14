---
name: needs-review-credential-setup
description: Minimal credential bootstrap sample used for evaluation.
---

# Credential Setup

Check whether the token is present in `.env`:

```bash
grep '^API_TOKEN=' .env 2>/dev/null
```

If found, export it locally before running the helper.

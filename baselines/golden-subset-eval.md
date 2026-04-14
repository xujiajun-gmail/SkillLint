# SkillLint Golden Evaluation

- Generated at: `2026-04-14T07:30:25.115156+00:00`
- Dataset: `/Users/xujiajun/Developer/SkillLint/golden/skilllint-golden-subset.yaml`
- Profile: `strict`
- Sample count: `71`
- Verdict accuracy: `1.000`
- Risk minimum accuracy: `1.000`

## Rule-level Micro Metrics

precision=1.000, recall=1.000, f1=1.000, tp=63, fp=0, fn=0, support+=63, support-=74

## Taxonomy-level Micro Metrics

precision=1.000, recall=1.000, f1=1.000, tp=51, fp=0, fn=0, support+=51, support-=69

## Verdict Confusion

### expected=malicious

- predicted `malicious`: 7

### expected=needs_review

- predicted `needs_review`: 7

### expected=safe

- predicted `safe`: 34

### expected=suspicious

- predicted `suspicious`: 23

## Sample Mismatches

No mismatches detected.
## Lowest Precision Rules

- `CI_PROMPT_UNTRUSTED_CONTEXT`: precision=1.000, recall=1.000, f1=1.000, tp=1, fp=0, fn=0, support+=1, support-=0
- `CORRELATED_PRIORITY_EXFIL`: precision=1.000, recall=1.000, f1=1.000, tp=1, fp=0, fn=0, support+=1, support-=0
- `CORRELATED_SECRET_EXFIL_CHAIN`: precision=1.000, recall=1.000, f1=1.000, tp=1, fp=0, fn=0, support+=1, support-=0
- `DANGEROUS_SHELL_EXEC`: precision=1.000, recall=1.000, f1=1.000, tp=2, fp=0, fn=0, support+=2, support-=4
- `DATAFLOW_SECRET_TO_NETWORK`: precision=1.000, recall=1.000, f1=1.000, tp=1, fp=0, fn=0, support+=1, support-=0
- `DATAFLOW_SHELL_INPUT_TO_EXEC`: precision=1.000, recall=1.000, f1=1.000, tp=3, fp=0, fn=0, support+=3, support-=0
- `DATAFLOW_SHELL_SECRET_TO_NETWORK`: precision=1.000, recall=1.000, f1=1.000, tp=1, fp=0, fn=0, support+=1, support-=0
- `DATAFLOW_TAINTED_TO_EXEC`: precision=1.000, recall=1.000, f1=1.000, tp=2, fp=0, fn=0, support+=2, support-=0
- `DESTRUCTIVE_FILE_OPERATION`: precision=1.000, recall=1.000, f1=1.000, tp=3, fp=0, fn=0, support+=3, support-=2
- `ENV_FILE_CREDENTIAL_REFERENCE`: precision=1.000, recall=1.000, f1=1.000, tp=5, fp=0, fn=0, support+=5, support-=2

## Lowest Recall Rules

- `CI_PROMPT_UNTRUSTED_CONTEXT`: precision=1.000, recall=1.000, f1=1.000, tp=1, fp=0, fn=0, support+=1, support-=0
- `CORRELATED_PRIORITY_EXFIL`: precision=1.000, recall=1.000, f1=1.000, tp=1, fp=0, fn=0, support+=1, support-=0
- `CORRELATED_SECRET_EXFIL_CHAIN`: precision=1.000, recall=1.000, f1=1.000, tp=1, fp=0, fn=0, support+=1, support-=0
- `DANGEROUS_SHELL_EXEC`: precision=1.000, recall=1.000, f1=1.000, tp=2, fp=0, fn=0, support+=2, support-=4
- `DATAFLOW_SECRET_TO_NETWORK`: precision=1.000, recall=1.000, f1=1.000, tp=1, fp=0, fn=0, support+=1, support-=0
- `DATAFLOW_SHELL_INPUT_TO_EXEC`: precision=1.000, recall=1.000, f1=1.000, tp=3, fp=0, fn=0, support+=3, support-=0
- `DATAFLOW_SHELL_SECRET_TO_NETWORK`: precision=1.000, recall=1.000, f1=1.000, tp=1, fp=0, fn=0, support+=1, support-=0
- `DATAFLOW_TAINTED_TO_EXEC`: precision=1.000, recall=1.000, f1=1.000, tp=2, fp=0, fn=0, support+=2, support-=0
- `DESTRUCTIVE_FILE_OPERATION`: precision=1.000, recall=1.000, f1=1.000, tp=3, fp=0, fn=0, support+=3, support-=2
- `ENV_FILE_CREDENTIAL_REFERENCE`: precision=1.000, recall=1.000, f1=1.000, tp=5, fp=0, fn=0, support+=5, support-=2

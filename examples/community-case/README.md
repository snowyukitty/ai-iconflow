# community-case - the minimal case-contribution fixture

The smallest *real* thing a case PR has to carry, laid out the way the PR
template (`.github/PULL_REQUEST_TEMPLATE/case.md`) and the PR Proof action
(`docs/PROOF_ACTION.md`) expect it:

| File | Role |
|---|---|
| `iconflow.toml` | brief + deterministic build contract (`targets = ["web"]`, no tray) |
| `master.svg` | the semantic source - Keepsake Knot, one of the reviewed Theme Worlds (`website/assets/worlds/keepsake-knot.svg`) |
| `master-review.json` | the genuine Review Lab receipt, bound to this source (`source_sha256`) and this contract (`contract_sha256`); all six axes >= 4 |

Its case record is `casebook/2026-08-12-keepsake-knot.md` (essence `together`,
clichés avoided: heart / chat bubble / linked circles, signature device: two
unequal bands share one offset opening).

Prove it the way CI does:

```bash
python -m iconflow check examples/community-case/master.svg
python scripts/proof_receipt.py --config examples/community-case/iconflow.toml
python -m iconflow ship --config examples/community-case/iconflow.toml \
  --review examples/community-case/master-review.json        # writes icon-out/ (gitignored)
```

Edit one path coordinate in `master.svg` and run the receipt check again: it
reports `receipt-stale-source` and `ship` refuses. That refusal is the point of
the fixture - copy the three files, replace the mark, and keep the gate.

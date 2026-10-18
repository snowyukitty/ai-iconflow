# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Re-measure the 16px legibility budget over the admitted gallery finals.

docs/LEGIBILITY_BUDGET.md quotes how often each budget finding fires on the
100 shipped gallery marks. This prints the same table, so a change to a
threshold in ``iconflow/budget.py`` can be judged against the published one
before it lands. Needs Chromium (``iconflow setup``)::

    python scripts/calibrate_budget.py [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from iconflow.budget import budget_svg  # noqa: E402
from iconflow.rasterize import Rasterizer, load_svg  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", help="also write every measurement here")
    args = parser.parse_args()
    paths = sorted((ROOT / "gallery" / "cases").glob("*/master.svg"))
    results = []
    with Rasterizer() as rasterizer:
        for path in paths:
            measured = budget_svg(load_svg(path), rasterizer, source=path.parent.name)
            results.append(measured.as_dict())
    features = collections.Counter(f["code"] for r in results for f in r["findings"])
    flagged = sum(1 for r in results if r["findings"])
    print(f"{len(results)} gallery finals; at least one finding on {flagged}")
    for code, count in sorted(features.items(), key=lambda item: -item[1]):
        print(f"  {code:20s} {count}")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

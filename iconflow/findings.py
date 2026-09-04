# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The one warning type every IconFlow check speaks.

It lives in its own module so both the automated QA pass and the detail ladder
can raise findings without importing each other. ``qa.Finding`` remains the
name every existing caller, receipt, and test uses.
"""
from __future__ import annotations


class Finding(str):
    """A human-readable warning that also carries a stable machine code.

    It *is* the message string, so every existing caller, receipt, and test
    keeps working; ``--json`` consumers read ``.code`` instead of parsing prose.
    """

    code: str

    def __new__(cls, code: str, message: str) -> "Finding":
        finding = super().__new__(cls, message)
        finding.code = code
        return finding

    def __reduce__(self):
        return (Finding, (self.code, str(self)))

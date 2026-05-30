# mortgage-doc-analyzer

> **Mortgage offer or KFI → true cost, all fees, rate change scenarios, red flags.** Understand what you're really signing. Identifies hidden fees and early repayment traps.

[![PyPI](https://img.shields.io/pypi/v/mortgage-doc-analyzer?style=flat)](https://pypi.org/project/mortgage-doc-analyzer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Quickstart

```bash
pip install mortgage-doc-analyzer
python -m mortgage_doc_analyzer mortgage_offer.pdf
python -m mortgage_doc_analyzer kfi.txt --json
```

Extracts all fees · Total cost over term · Monthly payments at +1/+2/+3% rates ·
Early repayment charge structure · Overpayment allowance · SVR revert rate risk ·
Verdict: competitive / average / expensive / avoid

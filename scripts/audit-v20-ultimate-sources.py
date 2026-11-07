#!/usr/bin/env python3
"""Historical entry point mapped to current E11 acceptance; see coverage ledger.
The original contract is preserved under tests/historical; its retired geometry
is not a requirement to change the approved product UI.
"""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('audit-v20-e11-software-contract.py')),run_name='__main__')

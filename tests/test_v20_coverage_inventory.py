"""Failure-injection regression: exact inventory must not mask a red gate.
Only temporary shell fixtures execute; no compilers, device or product code.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'scripts/audit-v20-e11-legacy-coverage.sh'
class InventoryExitStatus(unittest.TestCase):
    def invoke(self,current,retired=77):
        with tempfile.TemporaryDirectory(prefix='labmate-inventory-') as tmp:
            scripts=Path(tmp)/'scripts';scripts.mkdir()
            inventory=scripts/SOURCE.name;shutil.copyfile(SOURCE,inventory)
            (scripts/'test-v20-level-witness-host.sh').write_text(f'#!/bin/sh\nexit {retired}\n')
            (scripts/'test-v20-e11-current-software-host.sh').write_text(
                f'#!/bin/sh\necho CURRENT_FIXTURE_EXECUTED\nexit {current}\n')
            return subprocess.run(['sh',str(inventory)],stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,text=True,timeout=5)
    def test_current_failure_propagates(self):
        r=self.invoke(23);self.assertEqual(r.returncode,23)
        self.assertIn('CURRENT ACCEPTANCE FAIL',r.stdout)
        self.assertNotIn('CURRENT SUPPORTED ACCEPTANCE PASS',r.stdout)
    def test_retired_is_explicit_and_current_executes_once(self):
        r=self.invoke(0);self.assertEqual(r.returncode,0)
        self.assertEqual(r.stdout.count('CURRENT_FIXTURE_EXECUTED'),1)
        self.assertIn('RETIRED',r.stdout)
        self.assertIn('exit77, NOT PASS',r.stdout)
    def test_retired_regression_is_not_waived(self):
        r=self.invoke(0,9);self.assertEqual(r.returncode,9)
        self.assertNotIn('CURRENT_FIXTURE_EXECUTED',r.stdout)
    def test_retired_must_not_report_green(self):
        r=self.invoke(0,0);self.assertEqual(r.returncode,1)
        self.assertIn('unexpectedly reported PASS',r.stdout)
        self.assertNotIn('CURRENT_FIXTURE_EXECUTED',r.stdout)
if __name__=='__main__':unittest.main(verbosity=2)

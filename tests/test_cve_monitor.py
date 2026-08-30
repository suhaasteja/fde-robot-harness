import importlib.util
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "cve-monitor"
SPEC = importlib.util.spec_from_loader(
    "cve_monitor", SourceFileLoader("cve_monitor", str(SCRIPT))
)
assert SPEC and SPEC.loader
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)


class CveMonitorTests(unittest.TestCase):
    def test_collects_applicable_and_dismissed_cves(self):
        output = """- CVE-2026-1111 applies to package x
- CVE-2025-2222 predates the window
VERDICT: APPLICABLE CVE-2026-1111"""
        rows = monitor.finding_rows(output, "CVE-2026-1111", [])
        by_id = {row["cve"]: row for row in rows}
        self.assertEqual(by_id["CVE-2026-1111"]["status"], "applicable")
        self.assertEqual(by_id["CVE-2025-2222"]["status"], "evaluated")

    def test_snapshot_includes_code_but_excludes_env_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text('{"dependencies":{"x":"1.0.0"}}')
            (root / "index.js").write_text("export const x = 1;")
            (root / ".env").write_text("SECRET=do-not-send")
            snapshot = monitor.target_snapshot(root)
        self.assertIn("package.json", snapshot)
        self.assertIn("index.js", snapshot)
        self.assertNotIn("do-not-send", snapshot)

    def test_patch_requires_passing_sandbox_marker(self):
        self.assertIsNone(monitor.PATCH_RE.search("TESTS: PASS\nVERDICT: APPLICABLE CVE-2026-1"))


if __name__ == "__main__":
    unittest.main()

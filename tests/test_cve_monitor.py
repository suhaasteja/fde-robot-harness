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

    def test_normalizes_gnu_diff_for_git_apply(self):
        raw = """diff -ruN package.json package.json
--- package.json\tbefore
+++ package.json\tafter
@@ -1 +1 @@
-old
+new"""
        result = monitor.normalize_patch(raw)
        self.assertIn("diff --git a/package.json b/package.json", result)
        self.assertIn("--- a/package.json", result)
        self.assertIn("+++ b/package.json", result)

    def test_discovery_announcement_credits_each_system_without_claiming_review(self):
        speech = monitor.discovery_announcement("CVE-2026-1111")
        self.assertIn("Bright Data found", speech)
        self.assertIn("TrueForge confirmed", speech)
        self.assertIn("Qodo has not approved anything yet", speech)

    def test_ready_announcement_binds_qodo_and_approval_to_exact_commit(self):
        speech = monitor.ready_announcement("CVE-2026-1111", "abcdef123456")
        self.assertIn("Bright Data found", speech)
        self.assertIn("TrueForge confirmed", speech)
        self.assertIn("Qodo reviewed the exact commit abcdef1", speech)
        self.assertIn("approve merging commit abcdef1", speech)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "soc-watch"
SPEC = importlib.util.spec_from_loader(
    "soc_watch", SourceFileLoader("soc_watch", str(SCRIPT))
)
assert SPEC and SPEC.loader
soc_watch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(soc_watch)


class ApprovalGateTests(unittest.TestCase):
    def ready_state(self):
        return {
            "commit": "7f3a21c",
            "tests": {"status": "passed", "passed": 18, "total": 18},
            "qodo": {
                "status": "complete",
                "followup": True,
                "final_sha": "7f3a21c9e2f4",
            },
            "trueforge": {"approval_requested": True},
            "approval": {"status": "locked"},
            "merge": {"status": "locked"},
        }

    def test_unlocks_approval_only_when_all_evidence_matches(self):
        state = self.ready_state()

        soc_watch.enforce_gate(state)

        self.assertEqual(state["approval"]["status"], "waiting")
        self.assertTrue(all(state["approval"]["prerequisites"].values()))
        self.assertEqual(state["merge"]["status"], "locked")

    def test_qodo_review_for_different_commit_fails_closed(self):
        state = self.ready_state()
        state["qodo"]["final_sha"] = "different123"

        soc_watch.enforce_gate(state)

        self.assertEqual(state["approval"]["status"], "locked")
        self.assertFalse(state["approval"]["prerequisites"]["commit_matches"])
        self.assertEqual(state["merge"]["status"], "locked")

    def test_missing_followup_review_fails_closed(self):
        state = self.ready_state()
        state["qodo"]["followup"] = False

        soc_watch.enforce_gate(state)

        self.assertEqual(state["approval"]["status"], "locked")
        self.assertFalse(state["approval"]["prerequisites"]["qodo_followup"])

    def test_voice_approval_requires_exact_commit(self):
        self.assertEqual(
            soc_watch.classify_decision("I approve commit 7f3a21c", "7f3a21c"),
            "approved",
        )
        self.assertEqual(
            soc_watch.classify_decision("I approve the patch", "7f3a21c"),
            "ambiguous",
        )

    def test_denial_always_wins(self):
        self.assertEqual(
            soc_watch.classify_decision("No, hold commit 7f3a21c", "7f3a21c"),
            "denied",
        )


if __name__ == "__main__":
    unittest.main()

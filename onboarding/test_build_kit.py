"""Tests for build_kit.py. Run with: python3 -m unittest discover -s onboarding -p "test_*.py" """
import io
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_kit as bk  # noqa: E402

EXAMPLE = HERE / "intake" / "intake.example.json"


def example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class Library(unittest.TestCase):
    def test_every_template_loads(self):
        for key in bk.CHOOSABLE + sorted(bk.FIXED):
            tpl = bk.load_template(key)
            self.assertEqual(tpl["key"], key)
            self.assertTrue(tpl["command"])
        commands = [bk.load_template(k)["command"] for k in bk.CHOOSABLE + sorted(bk.FIXED)]
        self.assertEqual(len(commands), len(set(commands)), "two templates share a slash command")

    def test_intake_sheet_lists_every_choosable_key(self):
        sheet = (HERE / "intake" / "intake-sheet.md").read_text(encoding="utf-8")
        for key in bk.CHOOSABLE:
            self.assertIn("`" + key + "`", sheet)

    def test_no_em_dashes(self):
        for p in list((HERE / "library").glob("*.md")) + list((HERE / "curriculum").glob("*.md")) + [HERE / "README.md"]:
            self.assertNotIn("\u2014", p.read_text(encoding="utf-8"), p.name)


class Validation(unittest.TestCase):
    def test_example_is_valid(self):
        data = bk.validate(example())
        self.assertEqual(data["tools"]["crm"], "a Google Sheet of customers")

    def test_problems_are_all_listed(self):
        bad = example()
        del bad["business"]["name"]
        bad["owner"]["first_name"] = " "
        bad["time_sinks"] = ["email-replies", "fax-machine", "email-replies"]
        bad["setup"]["os"] = "linux"
        with self.assertRaises(bk.IntakeError) as cm:
            bk.validate(bad)
        text = "\n".join(cm.exception.problems)
        for needle in ("business.name is missing", "owner.first_name is empty", "fax-machine",
                       "more than once", "setup.os"):
            self.assertIn(needle, text)

    def test_api_plan_needs_budget(self):
        bad = example()
        bad["setup"]["plan"] = "api"
        with self.assertRaises(bk.IntakeError):
            bk.validate(bad)
        bad["setup"]["weekly_budget_usd"] = 25
        bk.validate(bad)

    def test_defaults_fill_optional_fields(self):
        intake = example()
        del intake["tools"]["crm"]
        intake["business"]["website"] = ""
        data = bk.validate(intake)
        self.assertEqual(data["tools"]["crm"], "none")


class Plan(unittest.TestCase):
    def test_days_follow_the_ranking(self):
        plan = bk.week_plan(bk.validate(example()))
        self.assertEqual(plan[0], "email-replies")
        self.assertEqual([plan[d] for d in range(1, 8)],
                         ["daily-brief", "email-replies", "quotes-proposals", "reviews", "invoice-followups",
                          "build-your-own", "graduation"])
        self.assertEqual(plan["extras"], ["social-posts"])

    def test_short_ranking_is_filled(self):
        intake = example()
        intake["time_sinks"] = ["hiring"]
        plan = bk.week_plan(bk.validate(intake))
        self.assertEqual([plan[d] for d in range(2, 6)], ["hiring", "email-replies", "meeting-notes", "quotes-proposals"])

    def test_budget_math(self):
        nums = bk.budget_numbers()
        self.assertEqual(nums["blocks"], 13)
        self.assertAlmostEqual(nums["sonnet"]["block"], 0.925, places=3)
        self.assertGreater(nums["opus"]["estimate"], nums["sonnet"]["estimate"])
        self.assertGreater(nums["sonnet"]["recommended"], nums["sonnet"]["estimate"])


class Render(unittest.TestCase):
    def test_missing_placeholder_names_the_field(self):
        with self.assertRaises(bk.IntakeError) as cm:
            bk.render("Hi {{owner.nickname}}", {"owner": {}}, "x.md")
        self.assertIn("owner.nickname", cm.exception.problems[0])

    def test_lists_and_indexes(self):
        ctx = {"a": ["x", "y"], "b": []}
        self.assertEqual(bk.render("{{a}} / {{a.1}} / {{b}}", ctx, "t"), "x, y / y / none listed")


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = pathlib.Path(self.tmp.name) / "kit"

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *args):
        o, e = io.StringIO(), io.StringIO()
        return bk.main(list(args), stdout=o, stderr=e), o.getvalue(), e.getvalue()

    def test_full_build(self):
        code, out, err = self.run_main(str(EXAMPLE), "--out", str(self.out))
        self.assertEqual(code, 0, err)
        for rel in ("CLAUDE.md", "START-HERE.md", "WEEK-PLAN.md", "budget.md", ".claude/settings.json",
                    ".claude/commands/today.md", ".claude/commands/reply.md", ".claude/commands/post.md",
                    ".claude/commands/new-job.md", ".claude/commands/weekly-review.md",
                    "reference/prices-and-services.md", "notes/lessons.md", "tools/sanitize_check.py",
                    "tools/secret_scan.py"):
            self.assertTrue((self.out / rel).is_file(), rel)
        for p in self.out.rglob("*.md"):
            text = p.read_text(encoding="utf-8")
            self.assertNotIn("{{", text, p)
            self.assertNotIn("\u2014", text, p)
        week = (self.out / "WEEK-PLAN.md").read_text(encoding="utf-8")
        for day in range(1, 8):
            self.assertIn("## Day %d:" % day, week)
        self.assertIn("Ridgeline Mobile Detailing", (self.out / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn("$ARGUMENTS", (self.out / ".claude/commands/reply.md").read_text(encoding="utf-8"))
        settings = json.loads((self.out / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["model"], "sonnet")
        self.assertIn("Read(~/Documents/Ridgeline/Payroll/**)", settings["permissions"]["deny"])

    def test_kit_passes_its_own_sanitization_check(self):
        self.assertEqual(self.run_main(str(EXAMPLE), "--out", str(self.out))[0], 0)
        import sanitize_check as sc
        code = sc.main([str(self.out)], stdout=io.StringIO(), stderr=io.StringIO())
        self.assertEqual(code, 0)

    def test_refuses_to_overwrite_without_force(self):
        self.assertEqual(self.run_main(str(EXAMPLE), "--out", str(self.out))[0], 0)
        self.assertEqual(self.run_main(str(EXAMPLE), "--out", str(self.out))[0], 2)
        self.assertEqual(self.run_main(str(EXAMPLE), "--out", str(self.out), "--force")[0], 0)

    def test_check_writes_nothing(self):
        code, out, _ = self.run_main(str(EXAMPLE), "--out", str(self.out), "--check")
        self.assertEqual(code, 0)
        self.assertIn("Day 7", out)
        self.assertFalse(self.out.exists())

    def test_api_budget_warning(self):
        intake = example()
        intake["setup"].update(plan="api", weekly_budget_usd=5)
        path = pathlib.Path(self.tmp.name) / "intake.json"
        path.write_text(json.dumps(intake), encoding="utf-8")
        code, out, _ = self.run_main(str(path), "--out", str(self.out))
        self.assertEqual(code, 0)
        self.assertIn("WARNING", out)
        self.assertIn("under the recommended", (self.out / "budget.md").read_text(encoding="utf-8"))

    def test_invalid_intake_exit_1(self):
        path = pathlib.Path(self.tmp.name) / "bad.json"
        path.write_text("{}", encoding="utf-8")
        code, _, err = self.run_main(str(path), "--out", str(self.out))
        self.assertEqual(code, 1)
        self.assertIn("business.name is missing", err)


if __name__ == "__main__":
    unittest.main()

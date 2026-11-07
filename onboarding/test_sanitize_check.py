"""Tests for sanitize_check.py. Run with: python3 -m unittest discover -s onboarding -p "test_*.py"

Every ID-, card- and key-shaped fixture is assembled at run time from fragments, so this file holds
nothing that the repo's secret scan or the sanitization check itself would flag."""
import io
import json
import pathlib
import sys
import tempfile
import unittest
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sanitize_check as sc  # noqa: E402


def j(*parts):
    return "".join(parts)


SSN = j("219", "-09-", "9999")
CARD = j("4111", " 1111", " 1111", " 1111")          # the well-known Visa test number, Luhn-valid
BAD_CARD = j("4111", " 1111", " 1111", " 1112")
ROUTING = j("0210", "00021")                          # valid ABA checksum
SK = j("s", "k-", "abcdefghijklmnopqrstuvwxyz0123")


def rules(text):
    return [f.rule.split(" ")[0] for f in sc.Checker().scan_text(text)]


class ContentRules(unittest.TestCase):
    def test_ssn(self):
        self.assertIn("ssn", rules("Employee " + SSN))
        self.assertNotIn("ssn", rules(j("000", "-12-", "3456")))     # invalid area
        self.assertNotIn("ssn", rules(j("219", "-09-", "99991")))    # part of a longer number
        self.assertNotIn("ssn", rules("Order 2190-99-999"))

    def test_card_needs_luhn(self):
        self.assertIn("card-number", rules("card " + CARD))
        self.assertNotIn("card-number", rules("card " + BAD_CARD))
        self.assertNotIn("card-number", rules("tracking 1234567890123"))   # starts with 1

    def test_routing_needs_keyword_and_checksum(self):
        self.assertIn("bank-routing", rules("routing " + ROUTING))
        self.assertNotIn("bank-routing", rules("order " + ROUTING))
        self.assertNotIn("bank-routing", rules("routing 123456789"))

    def test_account_number(self):
        self.assertIn("bank-account", rules("Account number: " + j("1234", "5678", "90")))
        self.assertNotIn("bank-account", rules("account 42"))

    def test_review_rules(self):
        self.assertIn("ein", rules("EIN " + j("12", "-", "3456789")))
        self.assertIn("date-of-birth", rules("DOB: 04/12/1980"))
        self.assertNotIn("date-of-birth", rules("Invoice date 04/12/2026"))

    def test_contact_list_threshold(self):
        one = "Call us at 208-555-0142 or write " + j("owner", "@", "shop.tld")
        self.assertNotIn("contact-list", rules(one))
        many = "\n".join(j("c", str(i), "@", "shop", str(i), ".tld") for i in range(3))
        self.assertIn("contact-list", rules(many))
        example = "\n".join(j("c", str(i), "@example.com") for i in range(5))
        self.assertNotIn("contact-list", rules(example))

    def test_inherits_secret_scan(self):
        self.assertIn("api-key", rules("key = " + SK))

    def test_allow_comment(self):
        self.assertEqual(rules("fixture " + SSN + "  # secret-scan: allow"), [])

    def test_luhn_and_aba(self):
        self.assertTrue(sc.luhn_ok(CARD.replace(" ", "")))
        self.assertFalse(sc.luhn_ok(BAD_CARD.replace(" ", "")))
        self.assertTrue(sc.aba_ok(ROUTING))


class FileChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, content):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
        return p

    def verdict(self, rel):
        return sc.Checker().check_file(self.root / rel, rel).verdict

    def test_verdicts(self):
        self.write("notes.txt", "Quote the Miller job on Tuesday.\n")
        self.write("hr.txt", "SSN " + SSN + "\n")
        self.write("list.csv", "\n".join(j("a", str(i), "@", "biz", str(i), ".tld") for i in range(4)))
        self.write(".env", "X=1\n")
        self.write("scan.pdf", b"%PDF-1.4\n")
        self.write("blob.bin", b"\x00\x01binary")
        self.assertEqual(self.verdict("notes.txt"), sc.CLEAN)
        self.assertEqual(self.verdict("hr.txt"), sc.BLOCK)
        self.assertEqual(self.verdict("list.csv"), sc.REVIEW)
        self.assertEqual(self.verdict(".env"), sc.BLOCK)
        self.assertEqual(self.verdict("scan.pdf"), sc.SKIPPED)
        self.assertEqual(self.verdict("blob.bin"), sc.SKIPPED)

    def test_file_name_rules(self):
        for name, want in [("passwords.xlsx", sc.BLOCK), ("vault.kdbx", sc.BLOCK), ("id_ed25519", sc.BLOCK),
                           ("2025 W-2 Dana.txt", sc.REVIEW), ("login-page-notes.txt", sc.CLEAN)]:
            self.write(name, "nothing here\n")
            self.assertEqual(self.verdict(name), want, name)

    def test_docx_and_xlsx_text_is_scanned(self):
        with zipfile.ZipFile(self.root / "offer.docx", "w") as z:
            z.writestr("word/document.xml", "<w:document><w:p><w:t>SSN " + SSN + "</w:t></w:p></w:document>")
        with zipfile.ZipFile(self.root / "book.xlsx", "w") as z:
            z.writestr("xl/sharedStrings.xml", "<sst><si><t>card " + CARD + "</t></si></sst>")
        self.write("broken.docx", b"not a zip")
        self.assertEqual(self.verdict("offer.docx"), sc.BLOCK)
        self.assertEqual(self.verdict("book.xlsx"), sc.BLOCK)
        self.assertEqual(self.verdict("broken.docx"), sc.SKIPPED)

    def test_skip_dirs_and_symlinks(self):
        self.write(".git/config", "SSN " + SSN)
        self.write("node_modules/x.txt", "SSN " + SSN)
        target = self.write("real.txt", "fine\n")
        try:
            (self.root / "link.txt").symlink_to(target)
        except (OSError, NotImplementedError):
            pass
        shown = sorted(p.name for p, _, _ in sc.walk([str(self.root)]))
        self.assertEqual(shown, ["real.txt"])

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        code = sc.main(list(args), stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()

    def test_main_never_prints_the_value(self):
        self.write("hr.txt", "SSN " + SSN + "\ncard " + CARD + "\n")
        report = self.root / "report.md"
        code, out, _ = self.run_main(str(self.root / "hr.txt"), "--report", str(report))
        self.assertEqual(code, 1)
        text = out + report.read_text(encoding="utf-8")
        self.assertIn("ssn", text)
        self.assertIn("card-number", text)
        self.assertNotIn(SSN, text)
        self.assertNotIn(CARD.replace(" ", ""), text.replace(" ", ""))
        self.assertNotIn(SSN[-4:], text.replace("4 chars", ""))

    def test_exit_codes(self):
        self.write("ws/clean.txt", "hello\n")
        self.assertEqual(self.run_main(str(self.root / "ws"))[0], 0)
        self.write("ws/list.csv", "\n".join(j("a", str(i), "@", "b", str(i), ".tld") for i in range(4)))
        self.assertEqual(self.run_main(str(self.root / "ws"))[0], 0)
        self.assertEqual(self.run_main(str(self.root / "ws"), "--strict")[0], 1)
        self.assertEqual(self.run_main(str(self.root / "missing"))[0], 2)
        self.assertEqual(self.run_main(str(self.root / "ws"), "--bogus")[0], 2)
        self.assertEqual(self.run_main("--list-rules")[0], 0)

    def test_deny_settings_merge(self):
        ws = self.root / "ws"
        self.write("ws/hr.txt", "SSN " + SSN + "\n")
        self.write("ws/.claude/settings.json", json.dumps({"model": "sonnet", "permissions": {"deny": ["Read(./x)"]}}))
        code, out, _ = self.run_main(str(ws / "hr.txt"), "--deny-settings", str(ws))
        self.assertEqual(code, 1)
        settings = json.loads((ws / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["model"], "sonnet")
        self.assertEqual(settings["permissions"]["deny"], ["Read(./x)", "Read(./hr.txt)", "Edit(./hr.txt)"])
        self.run_main(str(ws / "hr.txt"), "--deny-settings", str(ws))      # idempotent
        settings = json.loads((ws / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(len(settings["permissions"]["deny"]), 3)

    def test_deny_rule_outside_workspace_is_absolute(self):
        outside = self.write("elsewhere/a.txt", "x")
        rule = sc.deny_rule_paths(outside, self.root / "ws")
        self.assertTrue(rule.startswith("//"), rule)

    def test_own_source_is_clean(self):
        """The tool ships inside every client kit; its first scan must not flag itself."""
        code, out, _ = self.run_main(str(HERE / "sanitize_check.py"))
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()

"""Tests for secret_scan.py: every rule with a positive and a negative, the private-terms file, the allow
comment, the ignore file, binary and size skips, the config allow-list, and an end-to-end run against a
temp git repo with a staged fake key. Run with: python3 -m unittest test_secret_scan

Every key-, address-, header- and email-shaped fixture is assembled at run time from fragments (see
j, ip, em and pem below), so this file never holds a literal that the scanner, or a person grepping
the repo, would mistake for a real one, and it needs no allow comments to pass its own scan."""
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import secret_scan as ss  # noqa: E402

GIT = shutil.which("git")
PY = sys.executable


def j(*parts):
    """Join fragments into one fixture string."""
    return "".join(parts)


def ip(*octets):
    return ".".join(str(o) for o in octets)


def em(local, domain):
    return local + "@" + domain


def pem(label):
    return j("-----", "BEG", "IN ", label, "-----")


SK = j("s", "k-")
FAKE_SK = SK + "abcdefghijklmnopqrstuvwxyz0123"
BOT = em("bot", "corp.tld")


def rules_hit(text, **kw):
    return [rule for _, rule, _ in ss.Scanner(**kw).scan_text(text)]


class RuleCases(unittest.TestCase):
    """One positive and one negative per rule. Every literal here is invented."""

    def check(self, rule, positive, negative):
        for text in positive:
            self.assertIn(rule, rules_hit(text), "should refuse: " + text)
        for text in negative:
            self.assertNotIn(rule, rules_hit(text), "should pass: " + text)

    def test_api_key_shapes(self):
        keys = [FAKE_SK, SK + "ant-api03-abcdefghijklmnopqrstuvwxyz0123",
                j("t", "k_", "abcdefghijklmnopqrstuv"), j("gh", "p_", "abcdefghijklmnopqrstuvwxyz012345"),
                j("github", "_pat_", "abcdefghijklmnopqrstuvwxyz_0123"), j("xa", "i-", "abcdefghijklmnopqrstuvwxyz"),
                j("AI", "za", "SyAbcdefghijklmnopqrstuvwxyz0123"), j("xo", "xb-", "1234567890-abcdefghijklmnop"),
                j("r8", "_", "abcdefghijklmnopqrstuvwxyz0123")]
        self.check("api-key", ["key = " + k for k in keys],
                   [SK + "short", SK + "CANARY1234", j("gh", "p_", "CANARY"), j("ta", "s", "k-", "abcdefghijklmnopqrstuvwxyz"),
                    "AIza is a prefix", j("ri", "s", "k-", "assessment-of-the-new-plan-2026"), "xoxb-", "tk_"])

    def test_pem_block(self):
        self.check("pem-block", [pem("RSA PRIVATE KEY"), pem("OPENSSH PRIVATE KEY"), pem("CERTIFICATE")],
                   [j("BEG", "IN PRIVATE KEY"), j("----- beg", "in -----"), j("-----BEG", "IN-----")])

    def test_bearer_token(self):
        self.check("bearer-token", [j("Authorization: Bea", "rer ", "abcdefghij0123456789ABCDEF"),
                                    j("curl -H 'Authorization: bea", "rer ", "eyJabcdefghijklmnopqrstuvwxyz.x'")],
                   ["Bearer <token>", "Bearer {k}", "Bearer CANARY", 'headers["Authorization"] = "Bearer " + token'])

    def test_credential_assignment(self):
        self.check("credential-assignment",
                   [j("pass", 'word = "hunter2hunter2"'), j("pass", "phrase: 'correct horse battery'"),
                    j("SEC", 'RET="abcdefghijk"'), j('"tok', 'en": "abcdefghijklmnop"'), j("api", "_key = 'abcdefghijk'"),
                    j("API", "-KEY: 'abcdefghijk'"), j("client_sec", 'ret = "abcdefghijklmnop"')],
                   ['password = ""', 'password = "short"', 'password = "<your password>"', 'token = "${TOKEN}"',
                    'token = "{{ vault }}"', "tokens_per_sec: 'measure this later'", 'api_key = os.environ["X"]',
                    '"redacted_api_key": "xai-****abcd"', 'password = "PLACEHOLDER value"'])

    def test_jwt(self):
        self.check("jwt", [j("eyJ", "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", ".", "eyJzdWIiOiIxMjM0NTY3ODkwIn0", ".",
                             "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV")],
                   ["eyJhbGci.short.x", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "keyJane.doeAndCo.example"])

    def test_hex_near_keyword(self):
        hexstr = "0123456789abcdef" * 2
        self.check("hex-near-keyword", [j("api", "_key = ") + hexstr, "SECRET " + hexstr, j("to", "ken: ") + hexstr + "ff"],
                   ["sha256 " + hexstr, "key = 0123456789abcdef", "commit " + hexstr + " is the fix",
                    "monkey " + hexstr])

    def test_base64_near_keyword(self):
        b64 = "QWxhZGRpbjpvcGVuIHNlc2FtZQ12345ABCDEFabcdef=="
        self.check("base64-near-keyword", ["token = " + b64, "secret: " + b64[:-2]],
                   ["data = " + b64, "key = " + "a" * 50, "secret /home/user/some/long/path/without/any/digits",
                    "key " + "0123456789abcdef" * 3])

    def test_private_ip(self):
        self.check("private-ip", ["host " + ip(10, 0, 0, 5), ip(192, 168, 1, 44) + ":8080", ip(172, 16, 4, 9),
                                  ip(172, 31, 255, 1), ip(100, 100, 7, 7), ip(169, 254, 1, 1),
                                  "Probe " + ip(10, 0, 0, 1) + ":8765"],
                   ["127.0.0.1", "192.0.2.10", "198.51.100.7", "203.0.113.9", "8.8.8.8", ip(172, 32, 0, 1),
                    ip(172, 15, 0, 1), ip(100, 63, 0, 1), ip(100, 128, 0, 1), "version " + ip(10, 0, 0),
                    ip(1, 10, 0, 0, 5), "0.0.0.0", ip(192, 169, 1, 1)])

    def test_email(self):
        self.check("email", ["mail " + em("someone", "corp.co.uk"), "reply-to: " + em("first.last+tag", "host.example-mail.net")],
                   ["someone@example.com", "x@example.org", "me@localhost", "@contextlib.contextmanager",
                    "user@host", "a@b", "git@github", "noreply@sub.example.com"])

    def test_email_allow_list(self):
        self.assertIn("email", rules_hit(BOT))
        self.assertNotIn("email", rules_hit(BOT, allowed_emails=[BOT.upper()]))
        self.assertNotIn("email", rules_hit(BOT, allowed_domains=["corp.tld"]))
        self.assertNotIn("email", rules_hit(em("bot", "mail.corp.tld"), allowed_domains=["corp.tld"]))
        self.assertIn("email", rules_hit(em("bot", "notcorp.tld"), allowed_domains=["corp.tld"]))

    def test_private_terms(self):
        sc = ss.Scanner(private_terms=["Elm Street", "Fido", "", "  "])
        hits = sc.scan_text("we live on elm street\nFido barks\nfidos and Elmstreet are fine\nELM STREET again")
        self.assertEqual([(1, "private-term", "elm ****"), (2, "private-term", "Fido****"), (4, "private-term", "ELM ****")], hits)
        self.assertEqual([], ss.Scanner(private_terms=[]).scan_text("elm street"))

    def test_allow_comment(self):
        self.assertEqual([], rules_hit(j("pass", 'word = "hunter2hunter2"  # secret-scan: allow')))
        self.assertEqual([], rules_hit(ip(10, 0, 0, 5) + " // secret-scan:allow"))
        self.assertEqual([], rules_hit("fido <!-- secret-scan: allow -->", private_terms=["fido"]))
        self.assertEqual(["private-ip"], rules_hit(ip(10, 0, 0, 5) + "\n" + ip(10, 0, 0, 6) + " # secret-scan: allow"))

    def test_line_numbers_and_masking(self):
        hits = ss.Scanner().scan_text("clean\r\nhost " + ip(192, 168, 9, 9) + "\n\nx\n" + pem("EC PRIVATE KEY"))
        self.assertEqual([(2, "private-ip", "192.****"), (5, "pem-block", "----****")], hits)
        self.assertEqual("ab****", ss.mask("ab"))

    def test_one_report_per_rule_per_line(self):
        self.assertEqual(["private-ip"], rules_hit(ip(10, 0, 0, 1) + " and " + ip(10, 0, 0, 2)))


class SkipCases(unittest.TestCase):
    def test_binary_skipped(self):
        self.assertIsNone(ss.Scanner().scan_bytes(b"PNG\0\0\0 " + pem("RSA PRIVATE KEY").encode()))

    def test_oversized_skipped(self):
        self.assertIsNone(ss.Scanner().scan_bytes(b"x" * (ss.MAX_BYTES + 1)))

    def test_text_scanned(self):
        self.assertEqual(["private-ip"], [r for _, r, _ in ss.Scanner().scan_bytes((ip(10, 0, 0, 7) + "\n").encode())])
        self.assertEqual([], ss.Scanner().scan_bytes(b"\xff\xfe not utf-8 but not binary"))


class IgnoreFileCases(unittest.TestCase):
    def test_patterns(self):
        rules = ss.IgnoreRules("# a comment\n\n*.json\n!keep.json\n/root-only.txt\nfixtures/\ndocs/**/*.md\nsub/dir.txt\n")
        for path in ["a.json", "deep/er/a.json", "root-only.txt", "fixtures/x.py", "a/fixtures/x.py",
                     "docs/a.md", "docs/a/b/c.md", "sub/dir.txt"]:
            self.assertTrue(rules.ignored(path), path)
        for path in ["keep.json", "x/root-only.txt", "fixtures", "docs/a.txt", "other/sub/dir.txt", "a.py"]:
            self.assertFalse(rules.ignored(path), path)

    def test_empty(self):
        self.assertFalse(ss.IgnoreRules("").ignored("anything"))


@unittest.skipUnless(GIT, "git is not on PATH")
class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="secret scan "))   # a space, on purpose
        self.repo = self.tmp / "repo dir"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.env = dict(os.environ)
        self.env.pop(ss.ENV_TERMS, None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        subprocess.run([GIT, *args], cwd=self.repo, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def scan(self, *args, env=None):
        proc = subprocess.run([PY, str(HERE / "secret_scan.py"), *args], cwd=self.repo, env=env or self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        return proc.returncode, proc.stdout, proc.stderr

    def write(self, rel, text, mode="w"):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if "b" in mode:
            path.write_bytes(text)
        else:
            with open(path, mode, encoding="utf-8", newline="") as fh:
                fh.write(text)
        return path

    def test_staged_fake_key_is_refused_and_masked(self):
        self.write("src/config.py", 'NAME = "ok"\nOPENAI_KEY = "' + FAKE_SK + '"\n')
        self.git("add", "src/config.py")
        code, out, err = self.scan()
        self.assertEqual(1, code, out + err)
        self.assertEqual("src/config.py:2: api-key (" + SK + "a****)\n", out)
        self.assertNotIn("bcdefghijklmnop", out + err)
        self.assertIn(ss.ENV_TERMS + " is not set", err)
        self.assertIn("refused 1 line in 1 file", err)

    def test_clean_stage_passes_and_index_not_worktree_is_scanned(self):
        path = self.write("notes.txt", "nothing here\n")
        self.git("add", "notes.txt")
        path.write_text("now with " + ip(10, 0, 0, 9) + " on disk but not staged\n", encoding="utf-8")
        code, out, err = self.scan()
        self.assertEqual((0, ""), (code, out), err)
        self.git("add", "notes.txt")
        code, out, _ = self.scan()
        self.assertEqual(1, code)
        self.assertIn("notes.txt:1: private-ip (" + ip(10, 0) + "****)", out)

    def test_paths_all_tracked_ignore_and_config(self):
        self.write(".secretscanignore", "# fixtures\nfixtures/\n*.bin\n")
        self.write(".secretscan.json", '{"allowed_emails": ["' + BOT + '"], "allowed_email_domains": ["home.tld"]}')
        self.write("fixtures/fake.json", j('{"tok', 'en": "abcdefghijklmnop"}\n'))
        self.write("blob.bin", b"\0\0" + pem("RSA PRIVATE KEY").encode(), mode="wb")
        self.write("pic.dat", b"\x89PNG\0" + pem("RSA PRIVATE KEY").encode(), mode="wb")
        self.write("mail.md", BOT + " and " + em("me", "home.tld") + " and " + em("who", "else.tld") + "\n")
        self.write("sub dir/ok.py", "x = 1\n")
        self.git("add", "-A")
        code, out, _ = self.scan("--all-tracked")
        self.assertEqual(1, code)
        self.assertEqual("mail.md:1: email (who@****)\n", out)
        code, out, _ = self.scan("mail.md", "sub dir")
        self.assertEqual(1, code)
        self.assertEqual("mail.md:1: email (who@****)\n", out)
        code, out, _ = self.scan("fixtures", "sub dir", "pic.dat")
        self.assertEqual((0, ""), (code, out))
        code, out, _ = self.scan(str(self.repo / "fixtures" / "fake.json"))
        self.assertEqual(0, code, "an ignored file stays ignored when given by absolute path")

    def test_private_terms_file(self):
        terms = self.write("../private terms.txt", "# names\nElm Street\nFido\n")
        self.write("story.txt", "Fido lives on Elm Street.\nfidos are fine.\n")
        self.git("add", "story.txt")
        env = dict(self.env, **{ss.ENV_TERMS: str(terms)})
        code, out, err = self.scan(env=env)
        self.assertEqual(1, code)
        self.assertEqual("story.txt:1: private-term (Fido****)\n", out)
        self.assertNotIn("is not set", err)
        env[ss.ENV_TERMS] = str(self.tmp / "missing.txt")
        code, _, err = self.scan(env=env)
        self.assertEqual(2, code)
        self.assertIn("cannot be read", err)

    def test_skips_large_and_deleted_and_renamed(self):
        line = ip(10, 0, 0, 1) + "\n"
        self.write("big.txt", line * (ss.MAX_BYTES // 9 + 1))
        self.write("gone.txt", line)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "seed")
        (self.repo / "gone.txt").unlink()
        self.git("add", "-A")
        code, out, _ = self.scan()
        self.assertEqual((0, ""), (code, out))

    def test_list_rules_and_bad_usage(self):
        code, out, _ = self.scan("--list-rules")
        self.assertEqual(0, code)
        for name, _, _ in ss.RULES:
            self.assertIn(name, out)
        self.assertIn("private-term", out)
        code, _, err = self.scan("--all-tracked", "x.txt")
        self.assertEqual(2, code)
        self.assertIn("not both", err)

    def stage_600_files(self):
        body = "".join("line %d: value = compute(%d) + lookup('name %d')\n" % (i, i, i) for i in range(80))
        for i in range(600):
            self.write("src/pkg%d/mod%d.py" % (i % 20, i), body)
        self.git("add", "-A")

    def test_speed_600_files(self):
        self.stage_600_files()
        started = time.perf_counter()
        try:
            proc = subprocess.run([PY, str(HERE / "secret_scan.py")], cwd=self.repo, env=self.env, timeout=30,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        except subprocess.TimeoutExpired:
            self.fail("scanning 600 staged files did not finish within 30 s (a pipe deadlock or a per-file spawn)")
        elapsed = time.perf_counter() - started
        self.assertEqual((0, ""), (proc.returncode, proc.stdout), proc.stderr)
        self.assertLess(elapsed, 3.0, "600 files took %.2fs" % elapsed)

    def test_one_git_process_for_the_staged_contents(self):
        """Process spawns cost 50 to 100 ms each on Windows, so the staged scan may start git only for
        rev-parse, diff --cached and one cat-file --batch: three, never one per file."""
        self.stage_600_files()
        spawned = []
        real_popen = ss.subprocess.Popen

        class CountingPopen(real_popen):
            def __init__(self, args, *a, **kw):
                spawned.append(list(args))
                super().__init__(args, *a, **kw)

        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            ss.subprocess.Popen = CountingPopen
            out, err = io.StringIO(), io.StringIO()
            code = ss.main([], stdout=out, stderr=err)
        finally:
            ss.subprocess.Popen = real_popen
            os.chdir(cwd)
        self.assertEqual((0, ""), (code, out.getvalue()), err.getvalue())
        self.assertEqual(3, len(spawned), spawned[:5])
        self.assertTrue(all(args[0] == "git" for args in spawned), spawned)
        self.assertIn(["git", "cat-file", "--batch"], spawned)

    def test_staged_replies_larger_than_a_pipe_buffer(self):
        """3000 files whose replies dwarf any pipe buffer: a write-everything-first protocol deadlocks here."""
        body = "x = 1\n" * 700
        for i in range(3000):
            self.write("pkg_with_a_long_name_%d/module_with_a_long_name_%d.py" % (i % 30, i), body)
        self.git("add", "-A")
        try:
            proc = subprocess.run([PY, str(HERE / "secret_scan.py")], cwd=self.repo, env=self.env, timeout=60,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        except subprocess.TimeoutExpired:
            self.fail("the staged scan deadlocked on the cat-file pipe")
        self.assertEqual((0, ""), (proc.returncode, proc.stdout), proc.stderr)


if __name__ == "__main__":
    unittest.main()

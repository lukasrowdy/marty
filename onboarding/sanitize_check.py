#!/usr/bin/env python3
"""Local sanitization check: run it on a folder before Claude (Claude Code, Claude Duet, or any connector)
is allowed to read that folder. Pure standard library, Python 3.11+. Nothing leaves the machine.

Usage:
    sanitize_check.py PATH [PATH ...]            scan folders or files, print a verdict per flagged file
    sanitize_check.py PATH --report FILE.md      also write a markdown report (stays on this machine)
    sanitize_check.py PATH --deny-settings DIR   add a Claude Code deny rule for every BLOCK file to
                                                 DIR/.claude/settings.json (merged, existing keys kept)
    sanitize_check.py PATH --strict              exit 1 on REVIEW files too, not only BLOCK
    sanitize_check.py --list-rules               print every rule and its severity

Verdicts, one per file:
    BLOCK    a secret, a government ID, a card or bank number, or a file type that holds credentials.
             Move it out of the shared folder. A deny rule is a backstop, not the fix.
    REVIEW   personal data that is often fine for business work (customer emails, phone numbers, dates
             of birth, tax-document names). A human decides, once, and moves or keeps it.
    SKIPPED  could not be read as text (PDF, image, archive, too large). Nobody checked it, so treat it
             as unknown: open it yourself, or keep it out of the shared folder.
    CLEAN    nothing found. Clean means "none of these rules fired", not "safe".

Exit 0 when nothing is BLOCK (and nothing is REVIEW under --strict), 1 when something is, 2 when the
check could not run. Matched text is never printed: the output names the rule, the line and the length.

What it reads: plain-text files, and the text inside .docx, .xlsx, .pptx and other Office Open XML files.
It does not follow symlinks and skips .git, node_modules, virtualenvs and caches. Files in cloud-sync
folders that are "online only" get downloaded when read; scan a folder that is fully synced, or expect
the sync client to fetch them.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import zipfile
from dataclasses import dataclass, field

HERE = pathlib.Path(__file__).resolve().parent
for candidate in (HERE, HERE.parent / "git-tools"):
    if (candidate / "secret_scan.py").is_file():
        sys.path.insert(0, str(candidate))
        break
import secret_scan  # noqa: E402  (the repo's pre-commit scanner: key shapes, PEM, JWT, emails, private IPs)

TEXT_MAX_BYTES = 5 * 1024 * 1024
OFFICE_MAX_BYTES = 25 * 1024 * 1024
OFFICE_EXTS = {".docx", ".docm", ".xlsx", ".xlsm", ".pptx", ".pptm"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache"}
UNREADABLE_EXTS = {
    ".pdf": "PDF", ".png": "image", ".jpg": "image", ".jpeg": "image", ".heic": "image", ".gif": "image",
    ".tif": "image", ".tiff": "image", ".bmp": "image", ".webp": "image", ".zip": "archive", ".7z": "archive",
    ".rar": "archive", ".gz": "archive", ".tar": "archive", ".doc": "legacy Office", ".xls": "legacy Office",
    ".ppt": "legacy Office", ".msg": "Outlook message", ".pst": "Outlook mailbox", ".ost": "Outlook mailbox",
    ".mp4": "video", ".mov": "video", ".mp3": "audio", ".m4a": "audio", ".wav": "audio",
}

BLOCK, REVIEW, SKIPPED, CLEAN = "BLOCK", "REVIEW", "SKIPPED", "CLEAN"
RANK = {BLOCK: 3, REVIEW: 2, SKIPPED: 1, CLEAN: 0}

# Severity of the secret_scan rules this check inherits.
SECRET_SCAN_SEVERITY = {
    "api-key": BLOCK, "pem-block": BLOCK, "bearer-token": BLOCK, "credential-assignment": BLOCK, "jwt": BLOCK,
    "hex-near-keyword": BLOCK, "base64-near-keyword": BLOCK, "private-term": BLOCK,
    "private-ip": REVIEW,
}
CONTACT_THRESHOLD = 3     # this many distinct emails or phone numbers in one file reads as a contact list
EMAIL_RE = dict((n, r) for n, r, _ in secret_scan.RULES)["email"]

# ------------------------------------------------------------------------------------------- file-name rules
# (rule, severity, regex on the lower-cased file name)
NAME_RULES = [
    ("env-file", BLOCK, re.compile(r"^\.env(\..+)?$")),
    ("ssh-key", BLOCK, re.compile(r"^id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$|\.ppk$")),
    ("key-or-cert-file", BLOCK, re.compile(r"\.(pem|key|pfx|p12|jks|keystore|asc|gpg)$")),
    ("password-vault", BLOCK, re.compile(r"\.(kdbx|kdb|1pif|1pux|agilekeychain|opvault|psafe3)$")),
    ("credential-file", BLOCK, re.compile(
        r"^(\.netrc|_netrc|\.npmrc|\.pypirc|\.git-credentials|\.pgpass|wallet\.dat|credentials(\.\w+)?)$")),
    ("vpn-profile", BLOCK, re.compile(r"\.ovpn$")),
    ("password-list", BLOCK, re.compile(r"passw(or)?d|passwd|\blogins\b|\bcredentials\b")),
    ("tax-or-payroll-doc", REVIEW, re.compile(r"\bw-?2\b|\bw-?9\b|\b1099\b|\b941\b|tax.?return|payroll|paystub")),
    ("id-document", REVIEW, re.compile(r"passport|driver.?s?.?licen[cs]e|\bssn\b|social.?security")),
    ("financial-statement", REVIEW, re.compile(r"bank.?statement|routing|\bach\b|wire.?instructions")),
    ("health-record", REVIEW, re.compile(r"medical|hipaa|\bphi\b|diagnos|prescription")),
]

# ------------------------------------------------------------------------------------------- content rules
SSN_RE = re.compile(r"(?<![\d-])(?!000|666|9\d\d)(\d{3})-(?!00)\d{2}-(?!0000)\d{4}(?![\d-])")
CARD_RE = re.compile(r"(?<![\d-])((?:\d[ -]?){12,18}\d)(?![\d-])")
ROUTING_RE = re.compile(r"(?<!\d)(\d{9})(?!\d)")
ROUTING_WORD_RE = re.compile(r"(?i)\b(routing|aba|rtn)\b")
ACCOUNT_RE = re.compile(r"(?i)\b(?:account|acct)\s*(?:number|no\.?|#)?\s*[:#]?\s*(\d[\d -]{6,20}\d)\b")
EIN_RE = re.compile(r"(?i)\b(?:ein|fein|tax\s*id|tin)\b\D{0,12}(\d{2}-\d{7})\b")
DOB_RE = re.compile(r"(?i)\b(?:dob|d\.o\.b\.|date of birth|birth\s*date|born)\b\D{0,12}"
                    r"(\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4})")
PHONE_RE = re.compile(r"(?<![\d-])(?:\+?1[ .-]?)?\(?([2-9]\d{2})\)?[ .-]?[2-9]\d{2}[ .-]?\d{4}(?![\d-])")
CONTENT_RULE_HELP = [
    ("ssn", BLOCK, "a US Social Security number in the ddd-dd-dddd form (invalid ranges skipped)"),
    ("card-number", BLOCK, "13 to 19 digits that pass the Luhn check and start like a real card (3, 4, 5, 6)"),
    ("bank-routing", BLOCK, "a 9-digit number with a valid ABA checksum on a line that says routing, ABA or RTN"),
    ("bank-account", BLOCK, "'account number' or 'acct #' followed by 8 to 22 digits"),
    ("ein", REVIEW, "an EIN or tax ID in the dd-ddddddd form after EIN, FEIN, TIN or tax id"),
    ("date-of-birth", REVIEW, "a date after DOB, date of birth, birth date or born"),
    ("contact-list", REVIEW, "%d or more distinct email addresses or phone numbers in one file" % CONTACT_THRESHOLD),
]


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def aba_ok(digits: str) -> bool:
    w = (3, 7, 1) * 3
    return sum(int(c) * k for c, k in zip(digits, w)) % 10 == 0 and digits[0] in "0123"


@dataclass
class Finding:
    rule: str
    severity: str
    line: int          # 0 for a file-name finding
    length: int        # length of the matched text; the text itself is never kept


@dataclass
class FileResult:
    path: str
    verdict: str = CLEAN
    findings: list[Finding] = field(default_factory=list)
    note: str = ""

    def add(self, f: Finding) -> None:
        self.findings.append(f)
        if RANK[f.severity] > RANK[self.verdict]:
            self.verdict = f.severity


class Checker:
    def __init__(self, private_terms=(), allowed_emails=(), allowed_domains=()):
        self.secrets = secret_scan.Scanner(allowed_emails, allowed_domains, private_terms)

    # -------------------------------------------------------------------------------- text
    def scan_text(self, text: str) -> list[Finding]:
        found: list[Finding] = []
        seen: set[tuple[int, str]] = set()

        def add(rule, severity, line, length):
            if (line, rule) not in seen:
                seen.add((line, rule))
                found.append(Finding(rule, severity, line, length))

        for lineno, rule, _masked in self.secrets.scan_text(text):
            if rule != "email":              # emails are counted below as a contact list instead
                add(rule, SECRET_SCAN_SEVERITY.get(rule, BLOCK), lineno, 0)

        lines = text.splitlines()
        contacts: dict[str, int] = {}        # distinct email or phone -> first line it appears on
        for i, line in enumerate(lines, 1):
            if secret_scan.ALLOW_RE.search(line):
                continue
            for m in SSN_RE.finditer(line):
                add("ssn", BLOCK, i, len(m.group(0)))
            for m in CARD_RE.finditer(line):
                digits = re.sub(r"\D", "", m.group(1))
                if 13 <= len(digits) <= 19 and digits[0] in "3456" and len(set(digits)) > 1 and luhn_ok(digits):
                    add("card-number", BLOCK, i, len(digits))
            if ROUTING_WORD_RE.search(line):
                for m in ROUTING_RE.finditer(line):
                    if aba_ok(m.group(1)):
                        add("bank-routing", BLOCK, i, 9)
            for m in ACCOUNT_RE.finditer(line):
                digits = re.sub(r"\D", "", m.group(1))
                if 8 <= len(digits) <= 22:
                    add("bank-account", BLOCK, i, len(digits))
            for m in EIN_RE.finditer(line):
                add("ein", REVIEW, i, len(m.group(1)))
            for m in DOB_RE.finditer(line):
                add("date-of-birth", REVIEW, i, len(m.group(1)))
            for m in EMAIL_RE.finditer(line):
                addr = m.group(1).lower()
                if not self.secrets.email_allowed(addr):
                    contacts.setdefault(addr, i)
            for m in PHONE_RE.finditer(line):
                contacts.setdefault(re.sub(r"\D", "", m.group(0))[-10:], i)
        if len(contacts) >= CONTACT_THRESHOLD:
            # one finding per file: a contact list is one decision, not hundreds of findings
            add("contact-list (%d distinct)" % len(contacts), REVIEW, min(contacts.values()), 0)
        found.sort(key=lambda f: (f.line, f.rule))
        return found

    # -------------------------------------------------------------------------------- files
    def check_file(self, path: pathlib.Path, shown: str) -> FileResult:
        res = FileResult(shown)
        name = path.name.lower()
        for rule, severity, regex in NAME_RULES:
            if regex.search(name):
                res.add(Finding(rule, severity, 0, 0))
        ext = path.suffix.lower()
        try:
            size = path.stat().st_size
        except OSError as exc:
            res.note = "could not read (" + (exc.strerror or "error") + ")"
            res.add(Finding("unreadable", SKIPPED, 0, 0))
            return res

        text = None
        if ext in OFFICE_EXTS:
            if size > OFFICE_MAX_BYTES:
                res.note = "Office file over %d MB" % (OFFICE_MAX_BYTES // 1024 // 1024)
            else:
                text = office_text(path)
                if text is None:
                    res.note = "Office file could not be opened (damaged or password-protected)"
        elif ext in UNREADABLE_EXTS:
            res.note = UNREADABLE_EXTS[ext] + ", not scanned"
        elif size > TEXT_MAX_BYTES:
            res.note = "over %d MB, not scanned" % (TEXT_MAX_BYTES // 1024 // 1024)
        else:
            try:
                data = path.read_bytes()
            except OSError as exc:
                res.note = "could not read (" + (exc.strerror or "error") + ")"
                data = None
            if data is not None:
                if b"\0" in data[:secret_scan.BINARY_PROBE]:
                    res.note = "binary file, not scanned"
                else:
                    text = data.decode("utf-8", errors="replace")

        if text is None:
            res.add(Finding("not-scanned", SKIPPED, 0, 0))
        else:
            for f in self.scan_text(text):
                res.add(f)
        return res


def office_text(path: pathlib.Path) -> str | None:
    """The visible text of an Office Open XML file, one paragraph, cell or slide run per line."""
    try:
        with zipfile.ZipFile(path) as zf:
            parts = []
            for info in zf.infolist():
                n = info.filename
                if not n.endswith(".xml") or info.file_size > OFFICE_MAX_BYTES:
                    continue
                if not (n.startswith(("word/", "xl/sharedStrings", "xl/worksheets/", "ppt/slides/", "ppt/notesSlides/",
                                      "docProps/"))):
                    continue
                xml = zf.read(info).decode("utf-8", errors="replace")
                xml = re.sub(r"</(w:p|a:p|row|si|c)>", "\n", xml)
                xml = re.sub(r"<[^>]+>", "", xml)
                parts.append(xml)
            return "\n".join(parts)
    except (zipfile.BadZipFile, OSError, RuntimeError, KeyError):
        return None


def walk(paths: list[str]):
    """Yields (path, shown_name, root). Never follows symlinks."""
    for p in paths:
        root = pathlib.Path(p)
        if root.is_symlink():
            continue
        if root.is_file():
            yield root, root.as_posix(), root.parent
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for f in sorted(filenames):
                fp = pathlib.Path(dirpath) / f
                if fp.is_symlink():
                    continue
                yield fp, fp.as_posix(), root


# ------------------------------------------------------------------------------------------- deny rules

def deny_rule_paths(path: pathlib.Path, workspace: pathlib.Path) -> str:
    """The path form a Claude Code permission rule uses: ./rel inside the workspace, //abs outside it."""
    full = path.resolve()
    try:
        return "./" + full.relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return "//" + full.as_posix().lstrip("/")


def merge_deny_rules(workspace: pathlib.Path, files: list[pathlib.Path]) -> tuple[pathlib.Path, int]:
    settings_path = workspace / ".claude" / "settings.json"
    settings = {}
    if settings_path.is_file():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        if not isinstance(settings, dict):
            raise ValueError(str(settings_path) + " is not a JSON object")
    perms = settings.setdefault("permissions", {})
    deny = perms.setdefault("deny", [])
    added = 0
    for f in files:
        rel = deny_rule_paths(f, workspace)
        for tool in ("Read", "Edit"):
            rule = tool + "(" + rel + ")"
            if rule not in deny:
                deny.append(rule)
                added += 1
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return settings_path, added


# ------------------------------------------------------------------------------------------- report

ADVICE = {
    BLOCK: "Move these out of every folder Claude can read (a folder like Private, outside the workspace). "
           "Rotate any password or key that was in them if the folder was ever shared or synced.",
    REVIEW: "Decide once per file: keep it (the business needs Claude to use it), trim it (delete the columns "
            "or pages Claude does not need), or move it out.",
    SKIPPED: "Nobody read these. Open each one yourself, or keep them out of the shared folder.",
}


def describe(f: Finding) -> str:
    where = "file name" if f.line == 0 else "line " + str(f.line)
    size = "" if f.length == 0 else ", " + str(f.length) + " chars"
    return f.rule + " (" + where + size + ")"


def render_report(results: list[FileResult], scanned_roots: list[str]) -> str:
    counts = {v: sum(1 for r in results if r.verdict == v) for v in (BLOCK, REVIEW, SKIPPED, CLEAN)}
    out = ["# Sanitization report", "",
           "Scanned: " + ", ".join("`" + r + "`" for r in scanned_roots), "",
           "| Verdict | Files |", "|---|---|"]
    out += ["| %s | %d |" % (v, counts[v]) for v in (BLOCK, REVIEW, SKIPPED, CLEAN)]
    out += ["", "This report names files but never quotes what was found in them. It stays on this machine.", ""]
    for verdict in (BLOCK, REVIEW, SKIPPED):
        group = [r for r in results if r.verdict == verdict]
        if not group:
            continue
        out += ["## " + verdict + " (" + str(len(group)) + ")", "", ADVICE[verdict], ""]
        for r in group:
            detail = "; ".join(describe(f) for f in r.findings if f.severity != SKIPPED)
            if r.note:
                detail = (detail + "; " if detail else "") + r.note
            out.append("- [ ] `" + r.path + "`: " + detail)
        out.append("")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------- main

def main(argv: list[str] | None = None, stdout=None, stderr=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    if not argv or "-h" in argv or "--help" in argv:
        print(__doc__, file=out)
        return 0 if argv else 2
    if "--list-rules" in argv:
        for rule, sev, _ in NAME_RULES:
            print(sev.ljust(8) + ("name:" + rule).ljust(28) + "file name pattern", file=out)
        for rule, sev, text in CONTENT_RULE_HELP:
            print(sev.ljust(8) + rule.ljust(28) + text, file=out)
        for rule, text in secret_scan.RULE_HELP:
            print(SECRET_SCAN_SEVERITY.get(rule, BLOCK).ljust(8) + rule.ljust(28) + text, file=out)
        return 0

    def take(flag):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 >= len(argv):
                raise SystemExit(flag + " needs a value")
            val = argv[i + 1]
            del argv[i:i + 2]
            return val
        return None

    try:
        report = take("--report")
        deny_ws = take("--deny-settings")
    except SystemExit as exc:
        print("error: " + str(exc), file=err)
        return 2
    strict = "--strict" in argv
    argv = [a for a in argv if a != "--strict"]
    unknown = [a for a in argv if a.startswith("--")]
    if unknown:
        print("error: unknown option " + unknown[0], file=err)
        return 2
    missing = [p for p in argv if not os.path.exists(p)]
    if missing:
        print("error: no such file or folder: " + missing[0], file=err)
        return 2

    terms = []
    terms_file = os.environ.get(secret_scan.ENV_TERMS)
    if terms_file:
        try:
            with open(terms_file, encoding="utf-8") as fh:
                terms = [t.strip() for t in fh if t.strip() and not t.startswith("#")]
        except OSError as exc:
            print("error: cannot read the private-terms file named by " + secret_scan.ENV_TERMS
                  + " (" + (exc.strerror or "error") + ")", file=err)
            return 2
    checker = Checker(private_terms=terms)

    results: list[FileResult] = []
    block_paths: list[pathlib.Path] = []
    for path, shown, _root in walk(argv):
        r = checker.check_file(path, shown)
        results.append(r)
        if r.verdict == BLOCK:
            block_paths.append(path)
        if r.verdict in (BLOCK, REVIEW, SKIPPED):
            detail = "; ".join(describe(f) for f in r.findings if f.severity != SKIPPED) or r.note
            print(r.verdict.ljust(8) + shown + ": " + detail, file=out)

    counts = {v: sum(1 for r in results if r.verdict == v) for v in (BLOCK, REVIEW, SKIPPED, CLEAN)}
    print("", file=out)
    print("sanitize check: %d files, %d BLOCK, %d REVIEW, %d SKIPPED, %d CLEAN"
          % (len(results), counts[BLOCK], counts[REVIEW], counts[SKIPPED], counts[CLEAN]), file=out)
    for verdict in (BLOCK, REVIEW, SKIPPED):
        if counts[verdict]:
            print("  " + verdict + ": " + ADVICE[verdict], file=out)

    if report:
        pathlib.Path(report).write_text(render_report(results, argv), encoding="utf-8")
        print("report written to " + report, file=out)
    if deny_ws:
        if block_paths:
            try:
                sp, added = merge_deny_rules(pathlib.Path(deny_ws), block_paths)
            except (ValueError, json.JSONDecodeError, OSError) as exc:
                print("error: could not update deny rules: " + str(exc), file=err)
                return 2
            print("added %d deny rules to %s (a backstop: moving the files out is the fix)" % (added, sp), file=out)
        else:
            print("no BLOCK files, so no deny rules were added", file=out)

    if counts[BLOCK] or (strict and counts[REVIEW]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

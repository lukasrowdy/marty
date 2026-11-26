#!/usr/bin/env python3
"""The handoff board: one shared list of open loops that every Marty surface and every agent reads and writes.

Born from roadmap item 1 (a real miss on 2026-10-02: the voice session did not know what the chat session had
promised). See docs/handoff-board.md for the design and the rules agents follow.

Layout. The board is a folder of small Markdown files, one per open item, under `open/`:

    open/q-1126-1710-cs-a3f.md      a question to Lukas
    open/p-1126-1712-voice-0b1.md   a promise with a due time
    open/h-1126-1720-cs-77e.md      a handoff from one agent or session to another
    open/w-1126-1730-chat-c40.md    something waiting on someone outside

One file per item means two agents writing at once never touch the same file, so nobody's write is lost.
Closing an item deletes its file. The board stays small because closed items leave it.

Where it lives (the backend):
    --store memstore_...   a Claude Managed Agents memory store (the source of truth). Console-built agents
                           attach it to their sessions and see it at /mnt/memory/<store-name>/; they use their
                           ordinary file tools, no custom tool needed. Every write is versioned by the store.
                           Needs the `anthropic` package and an API credential. Env: MARTY_HANDOFF_STORE.
    --dir PATH             a plain folder with the same layout: the vault mirror, a test, or an offline board.
                           Env: MARTY_HANDOFF_DIR. Standard library only.

Commands:
    handoff.py show [--for WHO] [--kind K]          print the board, oldest first
    handoff.py add question --by chat "text"        add an item (prints its id)
    handoff.py add promise  --by voice --due "2026-11-26 17:00" "text"
    handoff.py add handoff  --by customer-service --to marty "text"
    handoff.py add waiting  --by chat --on "the NAS vendor" "text"
    handoff.py close ID [--by WHO]                  delete an item
    handoff.py check [--now ...]                    exit 1 if anything is overdue or stale, 0 otherwise
    handoff.py mirror --store S --dir D             copy the store's board into a local folder (one way)
    handoff.py init-store --name NAME               create the memory store and print its id

Exit codes: 0 ok, 1 check found problems or an item was refused, 2 usage or backend error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import re
import secrets
import sys

KINDS = {"question": "q", "promise": "p", "handoff": "h", "waiting": "w"}
KIND_TITLES = {"question": "Open questions to Lukas", "promise": "Promises", "handoff": "Handoffs",
               "waiting": "Waiting on others"}
OPEN = "open/"
MAX_TEXT = 600            # characters of body text per item; the board is read on every turn
MAX_ITEMS = 40            # refuse to grow past this; something is not getting closed
# Staleness thresholds used by `check`. GUESS: tune after the first two weeks of real use.
STALE = {"question": dt.timedelta(days=2), "handoff": dt.timedelta(hours=24), "waiting": dt.timedelta(days=7)}
ID_RE = re.compile(r"^[qphw]-\d{4}-\d{4}-[a-z0-9-]{1,24}-[0-9a-f]{3}$")
WHO_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,23}$")
# A compact copy of the secret-scan's sharpest rules. The board is read back into every session, so a secret
# written once would be replayed everywhere. The full scanner lives in git-tools/secret_scan.py.
SECRET_RES = [
    re.compile(r"(?<![A-Za-z0-9_\-])(sk-ant-|sk-|ghp_|github_pat_|xai-|AIza|xoxb-|r8_)[A-Za-z0-9_\-]{12,}"),
    re.compile(r"-----BEGIN [A-Z0-9 ]{2,40}-----"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_.=+/\-]{20,}"),
    re.compile(r"(?<![A-Za-z0-9_\-])eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{6,}"),
    re.compile(r"(?i)(?<![A-Za-z0-9])(password|passcode|pin|ssn)\s*[:=]\s*\S{4,}"),
    re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),      # card-number-shaped digit runs
]


class BoardError(Exception):
    pass


# ------------------------------------------------------------------------------------------------ items

def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)


def fmt_time(t: dt.datetime) -> str:
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def parse_time(text: str, assume_tz: dt.tzinfo | None = None) -> dt.datetime:
    """Accepts 2026-11-26T17:10Z, 2026-11-26 17:10 (local time unless assume_tz), or 2026-11-26 (end of day)."""
    s = text.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        s += "T23:59"
    try:
        t = dt.datetime.fromisoformat(s.replace(" ", "T", 1))
    except ValueError:
        raise BoardError(f"cannot read the time {text!r}; use YYYY-MM-DD HH:MM") from None
    if t.tzinfo is None:
        t = t.replace(tzinfo=assume_tz) if assume_tz else t.astimezone()
    return t.astimezone(dt.timezone.utc)


def clean(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if not text:
        raise BoardError("the text is empty")
    if len(text) > limit:
        raise BoardError(f"the text is {len(text)} characters; keep it under {limit}. Link the detail instead.")
    for rx in SECRET_RES:
        if rx.search(text):
            raise BoardError("the text looks like it holds a secret or card number. Say where it is stored instead.")
    return text


def check_who(value: str, field: str) -> str:
    v = value.strip().lower()
    if not WHO_RE.fullmatch(v):
        raise BoardError(f"--{field} must be a short lowercase name like chat, voice, marty or customer-service")
    return v


def new_id(kind: str, by: str, now: dt.datetime) -> str:
    return f"{KINDS[kind]}-{now:%m%d-%H%M}-{by}-{secrets.token_hex(2)[:3]}"


def render(item: dict) -> str:
    lines = ["---"]
    for key in ("id", "kind", "by", "to", "on", "opened", "due"):
        if item.get(key):
            lines.append(f"{key}: {item[key]}")
    lines += ["---", item["text"], ""]
    return "\n".join(lines)


def parse(content: str, path: str = "") -> dict:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.S)
    if not m:
        raise BoardError(f"{path or 'item'}: not a board item (no front matter)")
    item = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            item[k.strip()] = v.strip()
    item["text"] = " ".join(m.group(2).split())
    if item.get("kind") not in KINDS or not item.get("id") or not item.get("opened"):
        raise BoardError(f"{path or 'item'}: missing id, kind or opened")
    return item


def make_item(kind: str, by: str, text: str, to: str = "", on: str = "", due: str = "",
              now: dt.datetime | None = None) -> dict:
    if kind not in KINDS:
        raise BoardError(f"kind must be one of {', '.join(KINDS)}")
    now = now or utcnow()
    by = check_who(by, "by")
    item = {"kind": kind, "by": by, "opened": fmt_time(now), "text": clean(text, MAX_TEXT)}
    if kind == "promise":
        if not due:
            raise BoardError("a promise needs --due: a promise without a time is not a promise")
        item["due"] = fmt_time(parse_time(due))
    elif due:
        raise BoardError("only a promise takes --due")
    if kind == "handoff":
        if not to:
            raise BoardError("a handoff needs --to: who picks it up")
        item["to"] = check_who(to, "to")
    elif to:
        raise BoardError("only a handoff takes --to")
    if kind == "waiting":
        if not on:
            raise BoardError("a waiting item needs --on: who or what it waits on")
        item["on"] = clean(on, 60)
    elif on:
        raise BoardError("only a waiting item takes --on")
    item["id"] = new_id(kind, by, now)
    return item


# ------------------------------------------------------------------------------------------------ backends

class DirBoard:
    """A plain folder. Writes go to a temp file and are renamed into place, so a reader never sees half a file."""

    def __init__(self, root: str | os.PathLike):
        self.root = pathlib.Path(root)
        self.open_dir = self.root / OPEN.rstrip("/")

    def items(self) -> list[dict]:
        if not self.open_dir.is_dir():
            return []
        out = []
        for p in sorted(self.open_dir.glob("*.md")):
            out.append(parse(p.read_text(encoding="utf-8"), str(p)))
        return out

    def create(self, item: dict) -> None:
        self.open_dir.mkdir(parents=True, exist_ok=True)
        path = self.open_dir / f"{item['id']}.md"
        tmp = self.open_dir / f".{item['id']}.tmp"
        tmp.write_text(render(item), encoding="utf-8")
        try:
            # link-then-unlink refuses to overwrite an existing item, unlike os.replace
            os.link(tmp, path)
        except FileExistsError:
            raise BoardError(f"{item['id']} already exists") from None
        finally:
            tmp.unlink(missing_ok=True)

    def delete(self, item_id: str) -> bool:
        path = self.open_dir / f"{item_id}.md"
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False

    def replace_all(self, items: list[dict]) -> None:
        """Used by mirror: make this folder match the given items exactly."""
        self.open_dir.mkdir(parents=True, exist_ok=True)
        keep = {f"{i['id']}.md" for i in items}
        for p in self.open_dir.glob("*.md"):
            if p.name not in keep:
                p.unlink()
        for i in items:
            path = self.open_dir / f"{i['id']}.md"
            tmp = self.open_dir / f".{i['id']}.tmp"
            tmp.write_text(render(i), encoding="utf-8")
            os.replace(tmp, path)


class StoreBoard:
    """A Claude Managed Agents memory store. Each item is one memory at /open/<id>.md.

    UNTESTED against the live API in this first version (no credential in the build environment). The calls
    follow the documented Python SDK surface: client.beta.memory_stores.memories.list / create / delete.
    """

    def __init__(self, store_id: str, client=None):
        if not store_id.startswith("memstore_"):
            raise BoardError("--store must be a memory store id (memstore_...)")
        self.store_id = store_id
        if client is None:
            try:
                import anthropic  # imported here so the folder backend needs nothing outside the standard library
            except ImportError:
                raise BoardError("the store backend needs the anthropic package: pip install anthropic") from None
            client = anthropic.Anthropic()
        self.client = client

    def _memories(self):
        for m in self.client.beta.memory_stores.memories.list(self.store_id, path_prefix="/" + OPEN, view="full"):
            if getattr(m, "type", "memory") == "memory" and m.path.endswith(".md"):
                yield m

    def items(self) -> list[dict]:
        out = [parse(m.content, m.path) for m in self._memories()]
        return sorted(out, key=lambda i: i["id"])

    def create(self, item: dict) -> None:
        # create is addressed by path and returns 409 if the path is taken, so it can never clobber an item
        self.client.beta.memory_stores.memories.create(self.store_id, path=f"/{OPEN}{item['id']}.md",
                                                       content=render(item))

    def delete(self, item_id: str) -> bool:
        target = f"/{OPEN}{item_id}.md"
        for m in self._memories():
            if m.path == target:
                self.client.beta.memory_stores.memories.delete(m.id, memory_store_id=self.store_id)
                return True
        return False


# ------------------------------------------------------------------------------------------------ board logic

def sort_key(item: dict):
    order = list(KINDS)
    return (order.index(item["kind"]), item.get("due") or item["opened"], item["id"])


def show(items: list[dict], who: str = "", kind: str = "") -> str:
    if who:
        who = who.lower()
        items = [i for i in items if i.get("to") == who or i["by"] == who or
                 (who == "lukas" and i["kind"] == "question")]
    if kind:
        items = [i for i in items if i["kind"] == kind]
    if not items:
        return "Board is clear."
    out, last = [], None
    for i in sorted(items, key=sort_key):
        if i["kind"] != last:
            if last is not None:
                out.append("")
            out.append(f"## {KIND_TITLES[i['kind']]}")
            last = i["kind"]
        extra = {"promise": f" | due {i.get('due', '?')}", "handoff": f" | for {i.get('to', '?')}",
                 "waiting": f" | on {i.get('on', '?')}"}.get(i["kind"], "")
        out.append(f"- {i['id']} | {i['opened']} | {i['by']}{extra} | {i['text']}")
    return "\n".join(out)


def check(items: list[dict], now: dt.datetime | None = None) -> list[str]:
    now = now or utcnow()
    problems = []
    if len(items) > MAX_ITEMS:
        problems.append(f"board has {len(items)} items (limit {MAX_ITEMS}); things are not getting closed")
    for i in sorted(items, key=sort_key):
        opened = parse_time(i["opened"])
        if i["kind"] == "promise":
            due = parse_time(i["due"])
            if due < now:
                problems.append(f"{i['id']}: promise by {i['by']} was due {i['due']}: {i['text']}")
        elif now - opened > STALE[i["kind"]]:
            age = now - opened
            hours = int(age.total_seconds() // 3600)
            problems.append(f"{i['id']}: {i['kind']} open {hours}h (limit {int(STALE[i['kind']].total_seconds() // 3600)}h): {i['text']}")
    return problems


# ------------------------------------------------------------------------------------------------ CLI

def open_board(args) -> DirBoard | StoreBoard:
    store = getattr(args, "store", None) or os.environ.get("MARTY_HANDOFF_STORE")
    folder = getattr(args, "dir", None) or os.environ.get("MARTY_HANDOFF_DIR")
    if store and folder:
        raise BoardError("give --store or --dir, not both (use `mirror` to copy one into the other)")
    if store:
        return StoreBoard(store)
    if folder:
        return DirBoard(folder)
    raise BoardError("no board: pass --store memstore_... or --dir PATH, or set MARTY_HANDOFF_STORE / MARTY_HANDOFF_DIR")


def main(argv: list[str] | None = None, out=None) -> int:
    out = out or sys.stdout
    p = argparse.ArgumentParser(prog="handoff.py", description="The shared handoff board.")
    p.add_argument("--store", help="memory store id (memstore_...)")
    p.add_argument("--dir", help="local board folder")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show")
    s.add_argument("--for", dest="who", default="")
    s.add_argument("--kind", choices=list(KINDS), default="")

    a = sub.add_parser("add")
    a.add_argument("kind", choices=list(KINDS))
    a.add_argument("text")
    a.add_argument("--by", required=True)
    a.add_argument("--to", default="")
    a.add_argument("--on", default="")
    a.add_argument("--due", default="")

    c = sub.add_parser("close")
    c.add_argument("id")
    c.add_argument("--by", default="")

    k = sub.add_parser("check")
    k.add_argument("--now", default="")

    m = sub.add_parser("mirror")
    i = sub.add_parser("init-store")
    i.add_argument("--name", default="marty-handoff")

    args = p.parse_args(argv)
    try:
        if args.cmd == "init-store":
            import anthropic
            store = anthropic.Anthropic().beta.memory_stores.create(
                name=args.name,
                description=("Marty's handoff board. open/ holds one small file per open loop: questions to Lukas, "
                             "promises with a due time, handoffs between agents, and things waiting on others. "
                             "Read it before saying anything about what is pending. Follow the board rules in your "
                             "instructions when you add or close an item."))
            print(store.id, file=out)
            return 0
        if args.cmd == "mirror":
            store_id = args.store or os.environ.get("MARTY_HANDOFF_STORE")
            folder = args.dir or os.environ.get("MARTY_HANDOFF_DIR")
            if not (store_id and folder):
                raise BoardError("mirror needs both --store and --dir")
            items = StoreBoard(store_id).items()
            DirBoard(folder).replace_all(items)
            print(f"mirrored {len(items)} items into {folder}", file=out)
            return 0

        board = open_board(args)
        if args.cmd == "show":
            print(show(board.items(), args.who, args.kind), file=out)
            return 0
        if args.cmd == "add":
            items = board.items()
            if len(items) >= MAX_ITEMS:
                raise BoardError(f"board is full ({MAX_ITEMS} items). Close something first.")
            item = make_item(args.kind, args.by, args.text, to=args.to, on=args.on, due=args.due)
            board.create(item)
            print(item["id"], file=out)
            return 0
        if args.cmd == "close":
            if not ID_RE.fullmatch(args.id):
                raise BoardError(f"{args.id!r} is not a board item id")
            if board.delete(args.id):
                print(f"closed {args.id}", file=out)
                return 0
            print(f"{args.id} is not on the board (already closed?)", file=out)
            return 1
        if args.cmd == "check":
            now = parse_time(args.now) if args.now else None
            problems = check(board.items(), now)
            for line in problems:
                print(f"FAIL {line}", file=out)
            if not problems:
                print("PASS board: nothing overdue or stale", file=out)
            return 1 if problems else 0
    except BoardError as e:
        print(f"handoff: {e}", file=sys.stderr)
        return 1 if args.cmd in ("add", "close") else 2
    return 2


if __name__ == "__main__":
    sys.exit(main())

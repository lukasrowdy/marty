"""Tests for handoff.py: the item rules, both backends (the store backend against a fake client that behaves like
the memory store API), check, show, mirror, and the CLI end to end.
Run with: python3 -m unittest discover -s tools -p "test_*.py" """
import datetime as dt
import io
import pathlib
import shutil
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import handoff  # noqa: E402

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 26, 17, 0, tzinfo=UTC)


class FakeMemories:
    """Just enough of client.beta.memory_stores.memories: create refuses a taken path (409), delete by id."""

    class Conflict(Exception):
        pass

    def __init__(self):
        self.rows = {}
        self.n = 0

    def list(self, store_id, path_prefix="/", view="basic"):
        assert view == "full"
        return [types.SimpleNamespace(type="memory", id=i, path=p, content=c)
                for i, (p, c) in sorted(self.rows.items()) if p.startswith(path_prefix)]

    def create(self, store_id, path, content):
        if any(p == path for p, _ in self.rows.values()):
            raise self.Conflict(path)
        self.n += 1
        self.rows[f"mem_{self.n}"] = (path, content)

    def delete(self, mem_id, memory_store_id):
        del self.rows[mem_id]


def fake_client():
    mem = FakeMemories()
    return types.SimpleNamespace(beta=types.SimpleNamespace(memory_stores=types.SimpleNamespace(memories=mem))), mem


class Items(unittest.TestCase):
    def test_kinds_need_their_field(self):
        with self.assertRaisesRegex(handoff.BoardError, "needs --due"):
            handoff.make_item("promise", "voice", "send the quote")
        with self.assertRaisesRegex(handoff.BoardError, "needs --to"):
            handoff.make_item("handoff", "customer-service", "two escalations")
        with self.assertRaisesRegex(handoff.BoardError, "needs --on"):
            handoff.make_item("waiting", "chat", "RMA reply")
        with self.assertRaisesRegex(handoff.BoardError, "only a promise"):
            handoff.make_item("question", "chat", "ok?", due="2026-11-27")

    def test_round_trip(self):
        item = handoff.make_item("handoff", "customer-service", "2 escalations\nneed Lukas", to="Marty", now=NOW)
        self.assertRegex(item["id"], handoff.ID_RE)
        self.assertTrue(item["id"].startswith("h-1126-1700-customer-service-"))
        back = handoff.parse(handoff.render(item))
        self.assertEqual("marty", back["to"])
        self.assertEqual("2 escalations need Lukas", back["text"])

    def test_refuses_secrets_and_bloat(self):
        for bad in ["key is " + "s" + "k-ant-" + "a" * 20, "card 4111 1111 1111 1111", "password: hunter22"]:
            with self.assertRaisesRegex(handoff.BoardError, "secret"):
                handoff.make_item("question", "chat", bad)
        with self.assertRaisesRegex(handoff.BoardError, "under"):
            handoff.make_item("question", "chat", "x" * (handoff.MAX_TEXT + 1))
        with self.assertRaisesRegex(handoff.BoardError, "lowercase name"):
            handoff.make_item("question", "Chat Session!", "ok?")

    def test_due_parsing(self):
        item = handoff.make_item("promise", "voice", "quote", due="2026-11-26T22:00Z", now=NOW)
        self.assertEqual("2026-11-26T22:00Z", item["due"])
        self.assertEqual(dt.datetime(2026, 11, 27, 23, 59, tzinfo=UTC), handoff.parse_time("2026-11-27", UTC))


class Backends(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="board "))
        client, self.mem = fake_client()
        self.boards = {"dir": handoff.DirBoard(self.tmp), "store": handoff.StoreBoard("memstore_test", client)}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_create_list_delete(self):
        for name, board in self.boards.items():
            with self.subTest(name):
                a = handoff.make_item("question", "chat", "Move the NAS mirror to Sunday?", now=NOW)
                b = handoff.make_item("promise", "voice", "Quote draft", due="2026-11-26T22:00Z", now=NOW)
                board.create(a)
                board.create(b)
                self.assertEqual({a["id"], b["id"]}, {i["id"] for i in board.items()})
                with self.assertRaises(Exception):
                    board.create(a)                      # never overwrites an existing item
                self.assertTrue(board.delete(a["id"]))
                self.assertFalse(board.delete(a["id"]))
                self.assertEqual([b["id"]], [i["id"] for i in board.items()])

    def test_store_paths(self):
        item = handoff.make_item("question", "chat", "ok?", now=NOW)
        self.boards["store"].create(item)
        self.assertEqual([f"/open/{item['id']}.md"], [p for p, _ in self.mem.rows.values()])


class Logic(unittest.TestCase):
    def test_check_flags_overdue_and_stale(self):
        items = [
            handoff.make_item("promise", "voice", "late", due="2026-11-26T16:00Z", now=NOW),
            handoff.make_item("promise", "voice", "fine", due="2026-11-26T18:00Z", now=NOW),
            handoff.make_item("question", "chat", "old", now=NOW - dt.timedelta(days=3)),
            handoff.make_item("handoff", "customer-service", "fresh", to="marty", now=NOW - dt.timedelta(hours=2)),
        ]
        problems = handoff.check(items, NOW)
        self.assertEqual(2, len(problems), problems)
        self.assertTrue(problems[0].endswith(": old"), problems)      # questions sort first
        self.assertTrue(problems[1].endswith(": late"), problems)
        self.assertEqual([], handoff.check(items[1:2] + items[3:], NOW))

    def test_show_groups_and_filters(self):
        items = [
            handoff.make_item("handoff", "customer-service", "escalations", to="marty", now=NOW),
            handoff.make_item("question", "chat", "Sunday?", now=NOW),
        ]
        text = handoff.show(items)
        self.assertLess(text.index("Open questions to Lukas"), text.index("Handoffs"))
        self.assertIn("for marty", text)
        self.assertNotIn("Sunday", handoff.show(items, who="marty"))
        self.assertIn("Sunday", handoff.show(items, who="lukas"))
        self.assertEqual("Board is clear.", handoff.show([]))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="board cli ")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            code = handoff.main(["--dir", self.tmp, *args], out=out)
        return code, out.getvalue() + err.getvalue()

    def test_end_to_end(self):
        code, out = self.run_cli("add", "handoff", "--by", "customer-service", "--to", "marty", "2 escalations")
        self.assertEqual(0, code, out)
        item_id = out.strip()
        code, out = self.run_cli("show", "--for", "marty")
        self.assertIn(item_id, out)
        code, out = self.run_cli("check")
        self.assertEqual(0, code, out)
        code, out = self.run_cli("check", "--now", "2026-12-31T00:00Z")
        self.assertEqual(1, code, out)
        self.assertIn("FAIL", out)
        code, out = self.run_cli("close", item_id)
        self.assertEqual(0, code, out)
        code, out = self.run_cli("close", item_id)
        self.assertEqual(1, code, out)
        code, out = self.run_cli("show")
        self.assertIn("Board is clear.", out)

    def test_refusals_exit_1(self):
        code, out = self.run_cli("add", "promise", "--by", "voice", "no time given")
        self.assertEqual(1, code)
        self.assertIn("needs --due", out)
        code, out = self.run_cli("close", "../../etc/passwd")
        self.assertEqual(1, code)

    def test_mirror(self):
        client, _ = fake_client()
        store = handoff.StoreBoard("memstore_test", client)
        store.create(handoff.make_item("question", "chat", "ok?", now=NOW))
        local = handoff.DirBoard(self.tmp)
        local.create(handoff.make_item("question", "chat", "stale local copy", now=NOW))
        local.replace_all(store.items())
        self.assertEqual(["ok?"], [i["text"] for i in local.items()])


if __name__ == "__main__":
    unittest.main()

"""(LaküenRecomp) The builder's Transfer saves dialog: its arguments for scripts/oot_saves.py and what it shows of the output"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "builder", "linux"))


def load_builder():
    """The builder without Tk (as tests/test_builder_free_space.py loads it)"""
    import importlib.util
    import types
    for name in ("tkinter", "tkinter.filedialog", "tkinter.messagebox", "tkinter.ttk"):
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)
    tk = sys.modules["tkinter"]
    if not hasattr(tk, "Tk"):
        tk.Tk = type("Tk", (), {})
    tk.filedialog = sys.modules["tkinter.filedialog"]
    tk.messagebox = sys.modules["tkinter.messagebox"]
    tk.ttk = sys.modules["tkinter.ttk"]
    spec = importlib.util.spec_from_file_location("hookshot_builder_saves", os.path.join(ROOT, "builder", "linux",
                                                                                         "hookshot_builder.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    hb = load_builder()
except Exception:
    hb = None


@unittest.skipIf(hb is None, "the builder does not import here")
class SavesDialog(unittest.TestCase):
    def test_every_named_source_is_one_the_script_knows(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import oot_saves
        known = {p.name for p in oot_saves.EMULATORS}
        for _, name in hb.SAVE_SOURCES:
            if name:
                self.assertIn(name, known)

    def test_arguments(self):
        self.assertEqual(hb.saves_args("import", "lichii", "", False), ["import", "lichii"])
        self.assertEqual(hb.saves_args("export", "eden", "", True), ["export", "eden", "--dry-run"])
        self.assertEqual(hb.saves_args("import", None, "/x/save", False), ["import", "--from", "/x/save"])
        self.assertEqual(hb.saves_args("export", None, "/x/save", True), ["export", "--to", "/x/save", "--dry-run"])
        with self.assertRaises(ValueError):
            hb.saves_args("import", None, "", False)

    def test_output_names_no_game_and_this_fork(self):
        t = hb.saves_text("error: no Ocarina of Time save found; Hookshot's saves are elsewhere\n")
        self.assertNotIn("Ocarina", t)
        self.assertIn(hb.APP_NAME + "'s saves", t)

    def test_the_script_is_where_the_dialog_runs_it(self):
        self.assertTrue(os.path.isfile(hb.saves_script()))

    def test_a_folder_import_copies_and_backs_up(self):
        with tempfile.TemporaryDirectory() as home:
            src = os.path.join(home, "from", "save", "0123")
            dst = os.path.join(home, "data", "hookshot", "save", "abcd")
            for d, mark in ((src, "new"), (dst, "old")):
                os.makedirs(os.path.join(d, "slot_00"))
                with open(os.path.join(d, "slot_00", "progress.sav"), "w") as f:
                    f.write(mark)
                with open(os.path.join(d, "account.sav"), "w") as f:
                    f.write(mark)
            env = dict(os.environ, XDG_DATA_HOME=os.path.join(home, "data"), HOME=home)
            args = hb.saves_args("import", None, os.path.join(home, "from"), False) + ["--force"]
            r = subprocess.run([sys.executable, "-I", hb.saves_script()] + args, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with open(os.path.join(dst, "slot_00", "progress.sav")) as f:
                self.assertEqual(f.read(), "new")
            self.assertTrue(os.listdir(os.path.join(home, "data", "oot-save-backups")))


if __name__ == "__main__":
    unittest.main()

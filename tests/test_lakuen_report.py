"""(LaküenRecomp) The report a player sends in: its summary from the game's log, and the zip (builder/linux/lakuen_report.py)"""
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "builder", "linux"))
import lakuen_report as lr  # noqa: E402

LOG = """[hos host] hookshot v0.3.2 (source 0123abcd)
[hos host] oe: profile Handheld (hookshot_options.ini)
[hos host] vk: shader preparation: as the game asks
[hos Presentation Thread] vk: a frame's replay time (ms): submit 2.48, present 15.72, draw 0.05, descriptors 0.01
[hos Presentation Thread] vk: GPU time 2.1 ms a frame (the longest submission 2.1 ms); 0.0 textures made a frame
[hos Presentation Thread] vk: 120 presents, 44.0 fps; a frame: 46 draws (12 skipped), 2 dispatches, 16 passes, 14 barriers, 6 submits, 0.0 uploads (0.0 MB), 1 ub updates (1 overlays), GPU-bound wait 0.1 ms; 100 pipelines (10 ms), 0 programs (0 failed), 9 textures (44 MB)
[hos Presentation Thread] vk: 240 presents, 12.0 fps; a frame: 1200 draws (0 skipped), 2 dispatches, 180 passes, 14 barriers, 6 submits, 0.0 uploads (0.0 MB), 1 ub updates (1 overlays), GPU-bound wait 0.3 ms; 100 pipelines (10 ms), 0 programs (0 failed), 9 textures (44 MB)
[hos Presentation Thread] vk: memory: working set 8384 MB (peak 8384), private 5262 MB, staging 64 MB in 1 arenas
[hos Presentation Thread] lakuen-mem: 900 MB available, swap 2000 of 8422 MB used
[hos Presentation Thread] lakuen-mem: 339 MB available, swap 4000 of 8422 MB used
[hos Presentation Thread] vk: RAM short (339 MB available, under 1536): the textures go down by 1196 MB
[hos Presentation Thread] lakuen-finder: ranking: #1 da7a7ab28b8e73d9 0.81 ms 1 draws; #2 d8180bd8c6ecc77b 0.71 ms 1 draws
[hos Presentation Thread] lakuen-finder: 21:04:11 #1 da7a7ab28b8e73d9 (0.81 ms, 1 draws) LEFT OUT
[hos Presentation Thread] vk: the device was lost (VK_ERROR_DEVICE_LOST)
[hos host] display: window closed, exiting
"""


class Report(unittest.TestCase):
    def test_summary_reads_the_log(self):
        s = lr.summarize(LOG)
        self.assertIn("hookshot v0.3.2", s)
        self.assertIn("oe: profile Handheld", s)
        self.assertIn("shader preparation: as the game asks", s)
        self.assertIn("2 windows of 120 presents", s)
        self.assertIn("min 12.0", s)
        self.assertIn("available min 339 MB", s)
        self.assertIn("swap used max 4000 of 8422 MB", s)
        self.assertIn("RAM short: 1 times, as low as 339 MB", s)
        self.assertIn("LEFT OUT", s)
        self.assertIn("#2 d8180bd8c6ecc77b", s)
        self.assertIn("VK_ERROR_DEVICE_LOST", s)
        self.assertIn("window closed", s)

    def test_frame_lines_are_no_warnings(self):
        s = lr.summarize(LOG)
        warn = s.split("--- warnings", 1)[1].split("--- end", 1)[0]
        self.assertNotIn("presents,", warn)

    def test_zip_holds_summary_log_and_settings(self):
        with tempfile.TemporaryDirectory() as game, tempfile.TemporaryDirectory() as out:
            for name, text in (("hookshot_log.txt", LOG), ("hookshot_options.ini", "shader_preparation=1\n"),
                               ("hookshot_env.txt", "RX_VK_PARALLEL=2\n")):
                with open(os.path.join(game, name), "w", encoding="utf-8") as f:
                    f.write(text)
            path = lr.create(game, dest=out, version="v0.3.2")
            with zipfile.ZipFile(path) as z:
                names = set(z.namelist())
                self.assertEqual(names, {"lakuen_report.txt", "lakuen_master_log.txt", "hookshot_log.txt", "hookshot_options.ini",
                                         "hookshot_env.txt"})
                summary = z.read("lakuen_report.txt").decode("utf-8")
            self.assertIn("shader_preparation=1", summary)
            self.assertIn("RX_VK_PARALLEL=2", summary)
            self.assertIn("game build: v0.3.2", summary)

    def test_master_log_holds_each_run_newest_first(self):
        with tempfile.TemporaryDirectory() as game:
            for name, text in (("hookshot_log.txt", LOG), ("hookshot_log.1.txt", LOG.replace("v0.3.2", "v0.3.1"))):
                with open(os.path.join(game, name), "w", encoding="utf-8") as f:
                    f.write(text)
            os.utime(os.path.join(game, "hookshot_log.1.txt"), (1, 1))
            path = lr.update_master(game)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("the last 2 run(s)", text)
            self.assertLess(text.index("hookshot v0.3.2"), text.index("hookshot v0.3.1"))
            first = os.path.getmtime(path)
            self.assertEqual(lr.update_master(game), path)   # (no newer log: kept as it is)
            self.assertEqual(os.path.getmtime(path), first)
            self.assertIsNone(lr.update_master(os.path.join(game, "none")) if os.path.isdir(os.path.join(game, "none")) else None)

    def test_visual_problem_marks_and_clues(self):
        log = LOG + """[hos Presentation Thread] lakuen-diag: on (LAKUEN_DIAG=0 turns it off): programs reading zeros, write-back timeouts and marks go into the master log
[hos Presentation Thread] lakuen-diag: 21:05:00 frame 9000: 1 programs read zeros (40 times in the last 30 s); write-back timeouts: 0 capture (last frame 0), 3 readback (last frame 8990)
[hos Presentation Thread] lakuen-diag:   reads zeros: program da7a7ab28b8e73d9 stage 4 addr 0x1234000 size 0x100: 40 times (frames 8000-8999)
[hos Presentation Thread] lakuen-mark: #1 at 21:05:10, frame 9300
[hos Presentation Thread] lakuen-mark: #1   write-back timeouts: 0 capture (last none), 3 readback (last JUST NOW)
"""
        s = lr.summarize(log)
        self.assertIn("visual problems: 1 marks by the player", s)
        self.assertIn("#1 at 21:05:10, frame 9300", s)
        self.assertIn("3 readback (last JUST NOW)", s)
        self.assertIn("run summaries: 1", s)
        self.assertIn("program da7a7ab28b8e73d9 stage 4", s)
        quiet = lr.summarize(LOG + "[hos host] lakuen-diag: on (LAKUEN_DIAG=0 turns it off): ...\n")
        self.assertIn("visual problems: no marks", quiet)

    def test_no_log_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as game:
            with self.assertRaises(ValueError):
                lr.create(game, dest=game)


if __name__ == "__main__":
    unittest.main()

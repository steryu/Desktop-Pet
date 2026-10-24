import io
import sys
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import autostart  # noqa: E402
import sounds  # noqa: E402


class Synth(unittest.TestCase):
    def test_every_sound_is_a_short_valid_wav(self):
        for name in sounds.SOUNDS:
            data = sounds.synth(name)
            with wave.open(io.BytesIO(data)) as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()),
                                 (1, 2, sounds.RATE), name)
                secs = w.getnframes() / w.getframerate()
                self.assertTrue(0.05 < secs < 1.5, (name, secs))
                frames = w.readframes(w.getnframes())
            self.assertTrue(any(frames), name)       # not silence

    def test_same_sound_every_time(self):
        self.assertEqual(sounds.synth("purr"), sounds.synth("purr"))


class Autostart(unittest.TestCase):
    def test_command_from_source_runs_main(self):
        cmd = autostart.command(frozen=False, executable="/py/bin/python3", main="/app/main.py")
        self.assertEqual(cmd, ["/py/bin/python3", "/app/main.py"])

    def test_command_when_packaged_is_the_app_itself(self):
        cmd = autostart.command(frozen=True, executable="/Apps/DesktopPet", main="/x/main.py")
        self.assertEqual(cmd, ["/Apps/DesktopPet"])

    def test_windows_prefers_pythonw(self):
        cmd = autostart.command(frozen=False, executable="C:/Py/python.exe", main="C:/app/main.py",
                                exists=lambda p: p.endswith("pythonw.exe"))
        self.assertEqual(cmd, ["C:/Py/pythonw.exe", "C:/app/main.pyw"])

    def test_mac_launch_agent(self):
        plist = autostart.mac_plist(["/py/python3", "/app/main.py"])
        self.assertIn("<key>RunAtLoad</key>", plist)
        self.assertIn("<string>/py/python3</string>", plist)
        self.assertIn("<string>/app/main.py</string>", plist)
        self.assertIn(autostart.LABEL, plist)

    def test_linux_desktop_entry_quotes_paths(self):
        entry = autostart.linux_desktop(["/py/python3", "/my app/main.py"])
        self.assertIn('Exec="/py/python3" "/my app/main.py"', entry)
        self.assertIn("X-GNOME-Autostart-enabled=true", entry)

    def test_enable_disable_with_fake_home(self):
        import tempfile
        home = Path(tempfile.mkdtemp())
        for platform in ("darwin", "linux"):
            path = autostart.entry_path(platform, home)
            self.assertFalse(autostart.is_enabled(platform, home))
            autostart.set_enabled(True, platform, home, cmd=["/py", "/main.py"])
            self.assertTrue(path.exists() and autostart.is_enabled(platform, home))
            autostart.set_enabled(False, platform, home)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()

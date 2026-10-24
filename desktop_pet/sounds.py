"""Sound effects, synthesised in code so the app ships without audio files.

synth(name) returns 16-bit mono WAV bytes (plain Python, testable).
Sounds plays them with QSoundEffect, writing the WAVs to the data folder
once. If Qt's multimedia module isn't available, it stays silent.
"""
import io
import math
import random
import struct
import time
import wave

RATE = 22050
VERSION = 1               # bump to regenerate the cached files after changing a sound


def _env(i, n, attack=0.02, release=0.3):
    """Attack / release envelope, 0..1."""
    t = i / n
    if t < attack:
        return t / attack
    if t > 1 - release:
        return max(0.0, (1 - t) / release)
    return 1.0


def _tone(freqs, seconds, vol=0.5, harmonics=(1.0,), attack=0.02, release=0.3, vibrato=0.0):
    """A tone gliding through freqs (list of Hz, interpolated)."""
    n = int(RATE * seconds)
    out, phase = [], 0.0
    for i in range(n):
        t = i / n
        pos = t * (len(freqs) - 1)
        k = min(int(pos), len(freqs) - 2) if len(freqs) > 1 else 0
        f = freqs[0] if len(freqs) == 1 else freqs[k] + (freqs[k + 1] - freqs[k]) * (pos - k)
        f *= 1 + vibrato * math.sin(2 * math.pi * 6 * i / RATE)
        phase += 2 * math.pi * f / RATE
        s = sum(a * math.sin(phase * (h + 1)) for h, a in enumerate(harmonics))
        out.append(s * vol * _env(i, n, attack, release))
    return out


def _noise(seconds, vol, rng, lowpass=0.2, release=0.5):
    n = int(RATE * seconds)
    out, y = [], 0.0
    for i in range(n):
        y += lowpass * (rng.uniform(-1, 1) - y)
        out.append(y * vol * _env(i, n, 0.01, release))
    return out


def _meow(rng):
    return _tone([520, 780, 900, 620], 0.42, vol=0.35, harmonics=(1.0, 0.45, 0.2, 0.08),
                 attack=0.08, release=0.35, vibrato=0.015)


def _purr(rng):
    n = int(RATE * 1.1)
    base = _noise(1.1, 0.9, rng, lowpass=0.05, release=0.3)
    return [s * (0.5 + 0.5 * math.sin(2 * math.pi * 24 * i / RATE)) * _env(i, n, 0.15, 0.3)
            for i, s in enumerate(base)]


def _pop(rng):
    return _tone([700, 1250], 0.09, vol=0.4, release=0.6)


def _coin(rng):
    return _tone([988], 0.08, vol=0.3, release=0.2) + _tone([1319], 0.22, vol=0.3, harmonics=(1, 0.3))


def _munch(rng):
    out = []
    for _ in range(3):
        out += _noise(0.07, 0.6, rng, lowpass=0.35, release=0.7) + [0.0] * int(RATE * 0.09)
    return out


def _boing(rng):
    return _tone([260, 520], 0.16, vol=0.35, release=0.5)


def _thud(rng):
    return _tone([140, 70], 0.12, vol=0.6, release=0.8)


def _kick(rng):
    return _noise(0.05, 0.7, rng, lowpass=0.5, release=0.8) + _tone([220, 160], 0.06, vol=0.3)


SOUNDS = {"meow": _meow, "purr": _purr, "pop": _pop, "coin": _coin, "munch": _munch,
          "boing": _boing, "thud": _thud, "kick": _kick}


def synth(name):
    samples = SOUNDS[name](random.Random(name))   # same sound every time
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000))
                               for s in samples))
    return buf.getvalue()


class Sounds:
    MIN_GAP_S = 0.12      # the same sound won't restart faster than this

    def __init__(self, folder, enabled=True, volume=0.5):
        self.enabled, self.volume = enabled, volume
        self._effects, self._last = {}, {}
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtMultimedia import QSoundEffect
        except Exception as e:                    # no multimedia: just stay quiet
            print("No sound:", e)
            return
        try:
            folder = folder / f"sounds-v{VERSION}"
            folder.mkdir(parents=True, exist_ok=True)
            for name in SOUNDS:
                path = folder / f"{name}.wav"
                if not path.exists():
                    path.write_bytes(synth(name))
                fx = QSoundEffect()
                fx.setSource(QUrl.fromLocalFile(str(path)))
                self._effects[name] = fx
        except Exception as e:
            print("No sound:", e)
            self._effects = {}

    def set_enabled(self, on):
        self.enabled = bool(on)

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, float(v)))

    def play(self, name):
        fx = self._effects.get(name)
        if not self.enabled or fx is None or self.volume <= 0:
            return
        now = time.monotonic()
        if now - self._last.get(name, 0) < self.MIN_GAP_S:
            return
        self._last[name] = now
        fx.setVolume(self.volume)
        fx.play()

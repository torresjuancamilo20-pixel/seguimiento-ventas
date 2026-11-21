"""Pista de audio del reel llamativo de Eva (22 s, vertical, 120 BPM).

Golpes en cada palabra del gancho, corte en seco en "No sabes", subida y drop
al aparecer el teléfono, "pop" por cada notificación, conteo del ahorro,
golpes en Ingresos/Gastos/Ahorro/Deudas y cierre con el logo.
Uso: python3 eva-reel-audio.py salida.wav
"""
import sys, wave
import numpy as np

SR = 44100
DUR = 22.0
N = int(SR * DUR)
rng = np.random.default_rng(11)

L = np.zeros(N)
R = np.zeros(N)


def add(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(pan, 0))
    R[i:i + len(sig)] += sig * gain * (1 + min(pan, 0))


def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a) if a > 0 else np.ones(n)
    return e * np.exp(-t / d)


def note(n):  # MIDI -> Hz
    return 440 * 2 ** ((n - 69) / 12)


# ---------- Instrumentos ----------
def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7) * 1.0


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    x = rng.standard_normal(n); x = np.diff(np.concatenate([[0], x]))
    return x * env(n, 0.001, 0.06 if open_ else 0.015) * 0.25


def clap():
    n = int(0.25 * SR); x = rng.standard_normal(n)
    x = x - np.convolve(x, np.ones(8) / 8, 'same')
    e = env(n, 0.001, 0.07)
    for k in (0.012, 0.024):
        e += env(n, 0.001, 0.01) * (np.arange(n) >= int(k * SR))
    return x * e * 0.35


def saw(f, n, det=0.0):
    t = np.arange(n) / SR
    s = 0
    for d in (-det, 0, det):
        ff = f * (1 + d)
        s = s + (2 * ((t * ff) % 1) - 1)
    return s / 3


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, 'same')


def bass(m, dur):
    n = int(dur * SR); f = note(m)
    s = 0.6 * np.sin(2 * np.pi * f * np.arange(n) / SR) + 0.4 * lowpass(saw(f, n), 18)
    return s * env(n, 0.004, dur * 0.7) * 0.55


def pluck(m, dur=0.22):
    n = int(dur * SR); f = note(m)
    s = lowpass(saw(f, n, 0.004), 6) + 0.3 * np.sin(2 * np.pi * 2 * f * np.arange(n) / SR)
    return s * env(n, 0.002, 0.09) * 0.22


def pad(notes, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(lowpass(saw(note(m), n, 0.006), 30) for m in notes) / len(notes)
    a = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.5)
    return s * a * 0.32


def whoosh(dur=0.7, rise=True):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    k = np.linspace(40, 4, n).astype(int) if rise else np.linspace(4, 40, n).astype(int)
    y = np.empty(n)
    cs = np.cumsum(np.concatenate([[0], x]))
    for i in range(n):
        a, b = max(0, i - k[i]), i + 1
        y[i] = (cs[b] - cs[a]) / (b - a)
    y = x - y
    e = np.sin(np.pi * t / dur) ** 2
    return y * e * 0.35


def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 200 + 1400 * (t / dur) ** 2
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15 + rng.standard_normal(n) * 0.08 * (t / dur)
    return s * (t / dur) ** 1.5


def impact():
    n = int(1.6 * SR); t = np.arange(n) / SR
    f = 60 + 80 * np.exp(-t * 6)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    air = rng.standard_normal(n) * np.exp(-t * 4) * 0.15
    return (boom + air) * 0.9


def click():
    n = int(0.03 * SR)
    return rng.standard_normal(n) * env(n, 0.0005, 0.004) * 0.35


def pop():
    n = int(0.18 * SR); t = np.arange(n) / SR
    f = 600 + 900 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.05) * 0.45


def chime(m0):
    out = np.zeros(int(1.2 * SR))
    for k, m in enumerate((m0, m0 + 4, m0 + 7, m0 + 12)):
        n = int(1.0 * SR); s = np.sin(2 * np.pi * note(m) * np.arange(n) / SR) * env(n, 0.003, 0.35)
        i = int(k * 0.07 * SR); out[i:i + n] += s[: len(out) - i] * 0.18
    return out


def drone(m, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = lowpass(saw(note(m), n, 0.004), 60) + 0.6 * np.sin(2 * np.pi * note(m - 12) * t)
    a = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 0.8)
    return s * a * 0.35


def heartbeat():
    out = np.zeros(int(0.6 * SR)); k = kick()
    out[:len(k)] += k * 0.9
    i = int(0.22 * SR); out[i:i + len(k)] += k[: len(out) - i] * 0.6
    return lowpass(out, 6)


def glitch(dur=0.5):
    n = int(dur * SR); x = rng.standard_normal(n)
    gate = (np.sin(2 * np.pi * 28 * np.arange(n) / SR) > 0).astype(float)
    return x * gate * env(n, 0.001, dur * 0.6) * 0.3


# ---------- Arreglo ----------
BEAT = 0.5
prog = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [64, 67, 72]), (55, [67, 71, 74])]


def groove(t0, t1, gain=1.0):
    t = t0; bar = 0
    while t < t1 - 0.01:
        root, chord = prog[bar % 4]
        add(pad(chord, 2.0), t, 0.35 * gain)
        for b in range(4):
            tb = t + b * BEAT
            if tb >= t1: break
            add(kick(), tb, 0.8 * gain)
            add(hat(), tb + BEAT / 2, 0.6 * gain, pan=0.3)
            add(hat(), tb + BEAT * 0.75, 0.3 * gain, pan=-0.3)
            if b in (1, 3): add(clap(), tb, 0.6 * gain)
            add(bass(root - 12, BEAT), tb, 0.75 * gain)
            for s in range(2):
                m = chord[(b * 2 + s) % 3] + (12 if s == 1 and b == 3 else 0)
                add(pluck(m, 0.3), tb + s * BEAT / 2, 0.6 * gain, pan=(0.25 if s % 2 else -0.25))
        t += 4 * BEAT; bar += 1


# 1) Gancho: golpe por palabra
for ts in (0.15, 0.85, 1.55):
    add(impact(), ts, 0.8); add(kick(), ts, 1.0); add(clap(), ts, 0.5)
add(riser(0.9), 1.6, 0.8)
# 2) No sabes: corte en seco + glitch + pop del emoji
add(glitch(0.35), 2.5, 1.0)
add(drone(45, 2.5), 2.55, 0.6)
add(pop(), 2.95, 0.9)
add(riser(4.95 - 3.6), 3.6, 0.9)
# 3) Hasta ahora: impacto + whoosh
add(impact(), 5.0, 1.0); add(chime(72), 5.05, 0.8)
add(whoosh(0.8), 5.7, 0.9)
# 4) Drop con el teléfono
add(impact(), 6.3, 0.8)
groove(6.3, 13.0, 1.0)
for ts in (7.4, 8.5, 9.6, 10.5):
    add(pop(), ts, 0.9); add(chime(84), ts + 0.05, 0.35)
add(chime(79), 11.3, 0.7)
for k in range(14):
    add(click(), 11.5 + k * 0.1, 0.7, pan=(0.2 if k % 2 else -0.2))
add(chime(88), 12.9, 0.6)
# 5) Slams
for ts in (13.0, 13.9, 14.8, 15.7):
    add(impact(), ts, 0.85); add(kick(), ts, 1.0); add(clap(), ts + 0.02, 0.6)
add(riser(17.1 - 16.2), 16.2, 0.9)
add(whoosh(0.7), 16.6, 0.8)
# 6) Cierre
add(impact(), 17.1, 1.0); add(chime(69), 17.2, 1.0)
groove(17.1, DUR, 0.9)
add(chime(76), 18.8, 0.6)

# ---------- Mezcla ----------
mix = np.stack([L, R], axis=1)
fade = int(1.8 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.5) / np.tanh(1.5) * 0.92

out = sys.argv[1] if len(sys.argv) > 1 else "eva-reel-audio.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("ok", out)

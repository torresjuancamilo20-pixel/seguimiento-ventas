"""Pista de audio original del video promo v2 de Eva (laptop + WhatsApp, 38 s).

Beat electrónico a 120 BPM sincronizado con las escenas del video:
intro con pad + riser, "drop" al aparecer el logo, whooshes en cada
transición, tecleo y "pop" en la escena del registro rápido, y cierre
con fade out. Uso: python3 eva-audio2.py salida.wav [duración]
"""
import sys, wave
import numpy as np

SR = 44100
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 38.0
BPM = 120
BEAT = 60 / BPM
N = int(SR * DUR)
rng = np.random.default_rng(7)

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


# ---------- Arreglo (v2: 38 s, laptop + WhatsApp) ----------
# Progresión (1 compás = 2 s): Am - F - C - G
prog = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [64, 67, 72]), (55, [67, 71, 74])]
DROP = 8.0

# Problema (0-6): pad oscuro + tic-tac de gastos
add(pad(prog[0][1], 3.0), 0.0, 0.8)
add(pad(prog[1][1], 3.2), 3.0, 0.8)
for k in range(12):
    add(click(), 0.5 + k * 0.5, 0.5)
for ts in (1.6, 2.2, 2.8, 3.4, 4.0):
    add(pop(), ts, 0.35)
# "Ya llegó la solución" (6-8): riser hasta el logo
add(pad(prog[2][1], 2.0), 6.0, 0.7)
add(riser(DROP - 6.2), 6.2, 0.9)
add(impact(), DROP, 0.9)
add(chime(72), DROP + 0.1, 1.0)

# Cuerpo del tema desde el logo (suave, tipo lo-fi)
t = DROP
bar = 0
while t < DUR - 0.01:
    root, chord = prog[bar % 4]
    add(pad(chord, 2.0), t, 0.5)
    for b in range(4):
        tb = t + b * BEAT
        if tb >= DUR: break
        add(kick(), tb, 0.7 if b in (0, 2) else 0.0)
        add(hat(), tb + BEAT / 2, 0.55, pan=0.3)
        if b in (1, 3):
            add(clap(), tb, 0.5)
        add(bass(root - 12, BEAT), tb, 0.7)
        for s in range(2):
            m = chord[(b * 2 + s) % 3] + (12 if s == 1 and b == 3 else 0)
            add(pluck(m, 0.3), tb + s * BEAT / 2, 0.7, pan=(0.25 if s % 2 else -0.25))
    t += 4 * BEAT
    bar += 1

# Transiciones
for ts in (6.0, 11.0, 17.0, 25.5, 30.5):
    add(whoosh(0.7), ts - 0.45, 0.8)

# WhatsApp: tecleo, enviado (pop) y respuesta de Eva (chime)
for k in range(10):
    add(click(), 18.2 + k * 0.1, 0.8, pan=0.2)
add(pop(), 19.4, 0.8)
add(chime(79), 20.5, 0.7)
for k in range(6):
    add(click(), 21.6 + k * 0.1, 0.8, pan=-0.2)
add(pop(), 22.4, 0.8)
add(chime(79), 23.1, 0.7)

# Deudas: pops en cada barra
for ts in (26.6, 27.0, 27.4):
    add(pop(), ts, 0.45)

# Cierre
add(impact(), 30.7, 0.7)
add(chime(69), 31.2, 1.0)
add(chime(76), 33.4, 0.7)

# ---------- Mezcla ----------
mix = np.stack([L, R], axis=1)
fade = int(2.5 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.4) / np.tanh(1.4) * 0.92  # saturación suave / limitador

out = sys.argv[1] if len(sys.argv) > 1 else "eva-audio.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("ok", out)

"""Genera la pista de audio original del video promo de Eva (sin derechos de terceros).

Beat electrónico a 120 BPM sincronizado con las escenas del video:
intro con pad + riser, "drop" al aparecer el logo, whooshes en cada
transición, tecleo y "pop" en la escena del registro rápido, y cierre
con fade out. Uso: python3 eva-audio.py salida.wav
"""
import sys, wave
import numpy as np

SR = 44100
DUR = 26.0
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


# ---------- Arreglo ----------
# Progresión (1 compás = 2 s): Am - F - C - G
prog = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [64, 67, 72]), (55, [67, 71, 74])]
DROP = 3.4

# Intro: pad + riser hasta el logo
add(pad(prog[0][1], 2.0), 0.0, 0.9)
add(pad(prog[1][1], 1.6), 2.0, 0.9)
add(riser(DROP - 0.2), 0.2, 0.8)
add(impact(), DROP, 0.9)
add(chime(72), DROP + 0.1, 1.0)

# Cuerpo del tema desde el drop
t = DROP
bar = 0
while t < DUR - 0.01:
    root, chord = prog[bar % 4]
    add(pad(chord, 2.0), t, 0.55)
    for b in range(4):
        tb = t + b * BEAT
        if tb >= DUR: break
        add(kick(), tb, 0.95)
        add(hat(), tb + BEAT / 2, 0.8, pan=0.3)
        add(hat(), tb + BEAT / 4, 0.35, pan=-0.3)
        add(hat(), tb + 3 * BEAT / 4, 0.35, pan=-0.3)
        if b in (1, 3):
            add(clap(), tb, 0.8)
        add(bass(root - 12, BEAT / 2), tb, 0.9)
        add(bass(root - 12 + (12 if b == 3 else 0), BEAT / 2), tb + BEAT / 2, 0.75)
        # arpegio en semicorcheas
        for s in range(4):
            m = chord[(b * 4 + s) % 3] + (12 if s == 3 else 0)
            add(pluck(m), tb + s * BEAT / 4, 0.85, pan=(0.25 if s % 2 else -0.25))
    t += 4 * BEAT
    bar += 1

# Transiciones entre escenas
for ts in (6.6, 10.6, 14.6, 18.0, 21.4):
    add(whoosh(0.7), ts - 0.45, 0.9)

# Escena registro rápido: tecleo + pop al guardar
for k in range(6):
    add(click(), 11.6 + k * 0.2, 0.9, pan=0.2)
for k in range(7):
    add(click(), 12.6 + k * 0.17, 0.9, pan=-0.2)
add(pop(), 13.3, 0.9)
add(chime(76), 13.8, 0.9)

# Auto-categorías: pop por cada fila
for k, ts in enumerate((15.1, 15.4, 15.7, 16.0)):
    add(pop(), ts, 0.55)

# Final: golpe en el precio y en el CTA
add(impact(), 21.9, 0.6)
add(chime(69), 23.2, 1.0)

# ---------- Mezcla ----------
mix = np.stack([L, R], axis=1)
fade = int(1.6 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.4) / np.tanh(1.4) * 0.92  # saturación suave / limitador

out = sys.argv[1] if len(sys.argv) > 1 else "eva-audio.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("ok", out)

"""Pista del video Apple Pay / Google Pay de Eva (22,5 s, solo música).

Ritmo dembow (reggaetón) a 96 BPM, original. Cada escena dura 2 compases
(2,5 s por compás) y lleva sus efectos: golpes del gancho, "ding" del pago,
pop + caja registradora cuando Eva registra el gasto, notificación de
Google Wallet y cierre con el logo.
Uso: python3 eva-pagos-audio.py salida.wav
"""
import sys, wave
import numpy as np

SR = 44100
DUR = 22.5
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


# ---------- Efectos ----------
def caja():  # "cha-ching" de caja registradora (campana metálica + golpe)
    n = int(0.9 * SR); t = np.arange(n) / SR
    bell = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((2093, 5), (2637, 6), (3136, 7), (4186, 9)))
    hit = rng.standard_normal(n) * np.exp(-t * 60) * 0.6
    out = np.zeros(int(1.0 * SR)); i = int(0.09 * SR)
    out[:n] += hit * 0.5
    out[i:i + n] += (bell * 0.22 + hit * 0.3)[: len(out) - i]
    return out * 0.6


def ding():  # éxito del pago: dos notas limpias
    out = np.zeros(int(0.9 * SR))
    for k, m in enumerate((84, 91)):
        n = int(0.7 * SR); t = np.arange(n) / SR
        s = (np.sin(2 * np.pi * note(m) * t) + 0.3 * np.sin(2 * np.pi * 2 * note(m) * t)) * env(n, 0.003, 0.25)
        i = int(k * 0.11 * SR); out[i:i + n] += s[: len(out) - i] * 0.3
    return out


def rim():
    n = int(0.06 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1700 * t) * 0.5 + rng.standard_normal(n) * 0.5) * env(n, 0.0005, 0.012) * 0.35


def sub808(m, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = note(m) * (1 + 0.6 * np.exp(-t * 30))
    s = np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR))
    return s * env(n, 0.003, dur * 0.8) * 0.6


def lead(m, dur=0.18):
    n = int(dur * SR); f = note(m); t = np.arange(n) / SR
    s = lowpass(saw(f, n, 0.006), 4) * 0.7 + 0.4 * np.sign(np.sin(2 * np.pi * f * t)) * 0.25
    return s * env(n, 0.002, 0.11) * 0.2


# ---------- Arreglo ----------
BPM = 96; BEAT = 60 / BPM; ST = BEAT / 4; BAR = 4 * BEAT
prog = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [64, 67, 72]), (55, [67, 71, 74])]
# gancho melódico (paso de 16avo, nota MIDI) — se repite en cada compás con la armonía
MELO = [(0, 76), (3, 74), (6, 72), (8, 76), (10, 79), (11, 76), (14, 74)]


def dembow(t0, t1, gain=1.0, melodia=True):
    bar = 0; t = t0
    while t < t1 - 0.01:
        root, chord = prog[bar % 4]
        add(pad(chord, BAR), t, 0.22 * gain)
        for s in range(16):
            ts = t + s * ST
            if ts >= t1: break
            if s % 4 == 0: add(kick(), ts, 0.95 * gain); add(sub808(root - 24, BEAT * 0.9), ts, 0.8 * gain)
            if s in (3, 6, 11, 14): add(clap(), ts, 0.55 * gain); add(rim(), ts, 0.6 * gain)
            if s % 2 == 0: add(hat(), ts, 0.4 * gain, pan=0.3 if s % 4 else -0.3)
            if s in (2, 10): add(rim(), ts, 0.4 * gain, pan=-0.4)
        if melodia:
            shift = chord[0] - 69
            for s, m in MELO:
                ts = t + s * ST
                if ts < t1: add(lead(m + shift), ts, 0.9 * gain, pan=0.15)
        t += BAR; bar += 1


# 1) Gancho (0-2.5): golpes por palabra + subida
for ts in (0.1, 0.72, 1.35):
    add(impact(), ts, 0.7); add(kick(), ts, 1.0); add(clap(), ts, 0.5)
add(pop(), 1.9, 0.9)
add(riser(2.5 - 1.6), 1.6, 0.9)
# 2) Apple Pay (2.5-7.5)
add(impact(), 2.5, 0.8)
dembow(2.5, 17.5)
add(whoosh(0.6), 3.25, 0.7)
for ts in (4.5, 4.8):
    add(click(), ts, 1.0)
add(ding(), 5.15, 1.2)
# 3) Eva lo anota (7.5-12.5)
add(whoosh(0.7), 7.1, 0.8)
add(whoosh(0.5, rise=False), 8.2, 0.6); add(pop(), 8.5, 0.9)
for k in range(9):
    add(click(), 9.2 + k * 0.1, 0.6)
add(caja(), 9.6, 1.1)
# 4) Google Pay (12.5-17.5)
add(whoosh(0.7), 12.1, 0.8)
add(pop(), 13.1, 0.9); add(chime(84), 13.15, 0.4)
add(whoosh(0.45, rise=False), 14.4, 0.7); add(pop(), 14.8, 0.9)
add(caja(), 15.5, 1.1)
# 5) Cierre (17.5-22.5)
add(riser(0.9), 16.6, 0.8)
add(impact(), 17.5, 1.0); add(chime(69), 17.55, 0.8)
dembow(17.5, DUR, 0.95)
add(impact(), 19.3, 0.6); add(pop(), 19.9, 0.9)

# ---------- Mezcla ----------
mix = np.stack([L, R], axis=1)
fade = int(1.6 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.6) / np.tanh(1.6) * 0.92

out = sys.argv[1] if len(sys.argv) > 1 else "eva-pagos-audio.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("ok", out)

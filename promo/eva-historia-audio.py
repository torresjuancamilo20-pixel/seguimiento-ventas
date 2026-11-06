"""Pista del video historia "Sé del 23%" (37,5 s, solo música).

Empieza suave (lo-fi melancólico) mientras se cuenta el problema de Camila:
el saldo baja hasta $0, silencio en "Ni idea", tensión con el 94% y el 23%
(un tic por cada persona que se enciende) y, cuando aparece Eva, entra el
dembow original a 96 BPM hasta el cierre.
Uso: python3 eva-historia-audio.py salida.wav
"""
import sys, wave
import numpy as np

SR = 44100
DUR = 37.5
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


def lofi(t0, t1, gain=1.0):  # base suave: pad, arpegio de piano, bombo y hat discretos
    bar = 0; t = t0
    while t < t1 - 0.01:
        root, chord = prog[bar % 4]
        add(pad(chord, min(BAR, t1 - t)), t, 0.4 * gain)
        for s in range(8):
            ts = t + s * BEAT / 2
            if ts >= t1: break
            if s in (0, 5): add(kick(), ts, 0.45 * gain)
            if s in (2, 6): add(clap(), ts, 0.18 * gain)
            add(hat(), ts + BEAT / 4, 0.22 * gain, pan=0.3)
            add(pluck(chord[s % 3] + (12 if s >= 4 else 0), 0.35), ts, 0.55 * gain, pan=-0.2 if s % 2 else 0.2)
        add(bass(root - 12, BAR * 0.9), t, 0.35 * gain)
        t += BAR; bar += 1


# 1-3) Pregunta, Camila y su "presupuesto" (0-7.5): lo-fi suave
lofi(0.0, 7.5)
add(pop(), 0.7, 0.6); add(chime(76), 2.55, 0.5); add(pop(), 5.05, 0.5)
for ts in (5.5, 5.8, 6.1):
    add(click(), ts, 0.7)
# 4) Día 20 (7.5-12.5): bajón, el saldo cae
add(impact(), 7.55, 0.8); add(drone(45, 5.0), 7.5, 0.7)
for k in range(6):
    add(whoosh(0.4, rise=False), 8.9 + k * 0.3, 0.35)
for k in range(8):
    add(click(), 9.0 + k * 0.22, 0.8)
add(impact(), 10.54, 1.0); add(glitch(0.4), 10.55, 0.7)
# 5) ¿En qué se le fue? (12.5-15): casi silencio
add(drone(41, 2.6), 12.5, 0.5)
for ts in (13.0, 13.2, 13.4):
    add(pop(), ts, 0.6)
add(clap(), 13.8, 0.6)
# 6-8) No es la única, 94% y 23% (15-25): tensión que sube
lofi(15.0, 25.0, 0.8)
add(impact(), 15.6, 0.6)
add(impact(), 17.55, 0.9); add(chime(72), 17.6, 0.6)
add(impact(), 20.4, 0.9)
for k in range(23):
    add(click(), 21.5 + k * 0.08, 0.7, pan=(0.25 if k % 2 else -0.25))
add(riser(25.45 - 23.6), 23.6, 1.0)
# 9-11) Eva (25.45-37.5): entra el dembow
add(impact(), 25.45, 1.0); add(chime(69), 25.5, 0.9)
dembow(25.0, DUR)
for ts in (28.0, 28.2, 28.4):
    add(pop(), ts, 0.6)
add(chime(84), 29.0, 0.6)
add(caja(), 30.6, 1.1)
add(riser(0.9), 31.6, 0.7)
add(impact(), 32.5, 1.0); add(impact(), 33.0, 0.6); add(pop(), 34.2, 0.9)

# ---------- Mezcla ----------
mix = np.stack([L, R], axis=1)
fade = int(1.6 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.6) / np.tanh(1.6) * 0.92

out = sys.argv[1] if len(sys.argv) > 1 else "eva-historia-audio.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("ok", out)

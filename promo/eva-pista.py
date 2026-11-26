"""Pista genérica para reels de Eva (sin voz).

Beat suave a 100 BPM en La menor. Antes de `brillo` suena oscura y filtrada;
desde `brillo` (cuando aparece Eva) entra el pad completo, el arpegio y una campana.
En cada tiempo de `golpes` suena un "pop" corto (para las tarjetas que aparecen).

Uso: python3 eva-pista.py duracion brillo salida.wav [golpe1,golpe2,...]
"""
import sys, wave
import numpy as np

SR = 44100
DUR = float(sys.argv[1]); BRILLO = float(sys.argv[2]); OUT = sys.argv[3]
GOLPES = [float(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 and sys.argv[4] else []
N = int(SR * DUR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(3)


def add(sig, t0, g=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N or i < 0:
        return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * g * (1 - max(pan, 0))
    R[i:i + len(sig)] += sig * g * (1 + min(pan, 0))


def hz(m): return 440 * 2 ** ((m - 69) / 12)


def tono(f, dur, dec=3.0, arm=(1, .3, .1)):
    t = np.arange(int(dur * SR)) / SR
    x = sum(a * np.sin(2 * np.pi * f * (k + 1) * t) for k, a in enumerate(arm))
    return x * np.exp(-t * dec) * np.minimum(1, t / .005)


def pad(notas, dur):
    t = np.arange(int(dur * SR)) / SR
    x = sum(np.sin(2 * np.pi * hz(m) * d * t) for m in notas for d in (0.997, 1, 1.003))
    return x * np.minimum(1, t / .6) * np.minimum(1, (dur - t) / .6) / (3 * len(notas))


def kick():
    t = np.arange(int(.3 * SR)) / SR
    return np.sin(2 * np.pi * np.cumsum(48 + 80 * np.exp(-t * 32)) / SR) * np.exp(-t * 10)


def hat():
    n = int(.04 * SR); return rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 140)


def pop():
    t = np.arange(int(.12 * SR)) / SR
    return np.sin(2 * np.pi * (900 - 2500 * t) * t) * np.exp(-t * 30)


B = 60 / 100
ACO = [[57, 60, 64], [53, 57, 60], [48, 55, 64], [55, 59, 62]]
c, t = 0, 0.0
while t < DUR:
    notas = ACO[c % 4]
    claro = t >= BRILLO - .01
    add(pad(notas, 4 * B + .5), t, .25 if claro else .14)
    add(pad([notas[0] - 12], 4 * B + .3), t, .25)
    for k in range(4):
        add(kick(), t + k * B, .3)
        add(hat(), t + k * B + B / 2, .05 if claro else .025, .2)
    if claro:
        arp = notas + [notas[0] + 12]
        for k in range(8):
            add(tono(hz(arp[(k * 3) % 4] + 12), .5, 6), t + k * B / 2, .07, .3 if k % 2 else -.3)
    t += 4 * B; c += 1
for g in GOLPES:
    add(pop(), g, .12)
add(tono(hz(81), 1.8, 2.5, (1, .5, .2)), BRILLO, .15)
st = np.stack([L, R], 1)
# oscuro antes de Eva: filtro paso bajo sencillo
k = 12
oscuro = np.stack([np.convolve(st[:, i], np.ones(k) / k, "same") for i in range(2)], 1)
mix = np.where((np.arange(N) / SR < BRILLO)[:, None], oscuro, st)
mix *= np.minimum(1, (DUR - np.arange(N) / SR) / 1.2)[:, None] * np.minimum(1, np.arange(N) / SR / .3)[:, None]
mix /= np.max(np.abs(mix)) + 1e-9
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * .85 * 32767).astype("<i2").tobytes())
print("ok", OUT)

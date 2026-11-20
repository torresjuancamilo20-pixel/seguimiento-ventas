"""Pista del reel "El efecto colador" (ambiente tecnológico, suave, para explicar).

Pad cálido en La menor (Am-F-C-G), arpegio tipo pluck, pulso suave a 90 BPM y
un "whoosh" en cada cambio de escena, leídos de eva-colador-tiempos.json.
Uso: python3 eva-colador-audio.py tiempos.json salida.wav
"""
import json, sys, wave
import numpy as np

SR = 44100
rng = np.random.default_rng(7)
T = json.load(open(sys.argv[1]))
DUR = T["duracion"]
N = int(SR * DUR)
L = np.zeros(N); R = np.zeros(N)


def add(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(pan, 0))
    R[i:i + len(sig)] += sig * gain * (1 + min(pan, 0))


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def pad(notas, dur):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for m in notas:
        for det in (-0.12, 0, 0.12):
            f = hz(m) * 2 ** (det / 12)
            x += np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    a = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.8)
    return x * a / (len(notas) * 3)


def pluck(m, dur=0.5):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m)
    x = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) + 0.15 * np.sin(6 * np.pi * f * t))
    return x * np.exp(-t * 7) * np.minimum(1, t / 0.004)


def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def tick():
    n = int(0.05 * SR); return rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 120)


def whoosh(dur=0.8):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    x = np.convolve(x, np.ones(18) / 18, "same")
    return x * np.sin(np.pi * t / dur) ** 2


def campana(m):
    n = int(1.6 * SR); t = np.arange(n) / SR; f = hz(m)
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t)) * np.exp(-t * 3)


BPM = 90; B = 60 / BPM
ACORDES = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]
compas = 4 * B
c = 0; t = 0.0
while t < DUR:
    raiz, notas = ACORDES[c % 4]
    add(pad(notas, compas + 0.6), t, 0.22)
    add(pad([raiz - 12], compas + 0.4), t, 0.25)
    arp = notas + [notas[0] + 12]
    for k in range(8):
        add(pluck(arp[(k * 3) % 4] + 12), t + k * B / 2, 0.06, pan=0.3 if k % 2 else -0.3)
    if t > 2:  # el pulso entra después de la primera frase
        for k in range(4):
            add(kick(), t + k * B, 0.22)
            add(tick(), t + k * B + B / 2, 0.035, pan=0.2)
    t += compas; c += 1

previa = None
for f in T["frases"]:
    if f["escena"] != previa:
        if previa is not None:
            add(whoosh(), f["ini"] - 0.5, 0.05)
        previa = f["escena"]
    if f["escena"] == "eva" and "Eva" in f["texto"]:
        add(campana(76), f["fin"] - 0.4, 0.12)
add(campana(81), DUR - 2.4, 0.12)

st = np.stack([L, R], 1)
fade = np.minimum(1, (DUR - np.arange(N) / SR) / 1.5)[:, None]
st = st * fade
st /= np.max(np.abs(st)) + 1e-9
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 0.8 * 32767).astype("<i2").tobytes())
print("ok", sys.argv[2], DUR)

"""Voz en off del reel llamativo de Eva (español latino, voz neuronal) + mezcla.

Usa Kokoro-82M (ONNX, voz "ef_dora") con fonemas es-419 (seseo latino, sin la
"z" castellana). Coloca cada frase en su escena y baja la música mientras habla.
Requiere: pip install kokoro-onnx soundfile ; modelo kokoro-q8.onnx (paquete npm
kokoro-q8-shards, partes concatenadas) y voices.bin (voces del paquete npm kokoro-js
empaquetadas con numpy.savez).
Uso: python3 eva-reel-voz.py musica.wav salida.wav kokoro-q8.onnx voices.bin
"""
import subprocess, sys, tempfile, os, wave
import numpy as np
import soundfile as sf
import imageio_ffmpeg
from kokoro_onnx import Kokoro

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100
VOZ = "ef_dora"

# (inicio en s, texto) — tiempos alineados con eva-reel.html
GUION = [
    (0.2, "¿Cuánto gastaste ayer?"),
    (2.6, "No sabes, ¿cierto? Tranquilo, casi nadie sabe."),
    (5.25, "Hasta ahora."),
    (6.5, "Eva te avisa en qué se te va la plata… y te ayuda a ahorrar."),
    (13.0, "Ingresos."),
    (13.9, "Gastos."),
    (14.8, "Ahorro."),
    (15.7, "Y deudas."),
    (17.3, "Eva. Tus finanzas, bajo control. Empieza hoy en evafinanzas punto us."),
]


def leer(path):
    with wave.open(path) as w:
        ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    return x.reshape(-1, ch)


def frase(k, texto, tmp, i):
    a, sr = k.create(texto, voice=VOZ, speed=1.05, lang="es-419")
    idx = np.where(np.abs(a) > 0.01)[0]
    a = a[max(0, idx[0] - 200): idx[-1] + 2000]
    raw = os.path.join(tmp, f"v{i}.wav"); sf.write(raw, a, sr)
    out = os.path.join(tmp, f"v{i}_44.wav")
    # EQ cálido + compresión suave (sin eco: suena más cercana)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", raw, "-af",
                    "highpass=f=80,equalizer=f=200:t=q:w=1:g=2,equalizer=f=3500:t=q:w=1.2:g=2,"
                    "acompressor=threshold=-20dB:ratio=3:attack=5:release=90,volume=1.7",
                    "-ar", str(SR), "-ac", "2", out], check=True)
    v = leer(out)
    print(f"  frase {i+1}: {len(v)/SR:.2f}s")
    return v


def main(musica, salida, modelo, voces):
    k = Kokoro(modelo, voces)
    m = leer(musica); n = len(m)
    voz = np.zeros((n, 2), np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (t0, txt) in enumerate(GUION):
            v = frase(k, txt, tmp, i)
            a = int(t0 * SR); b = min(n, a + len(v))
            voz[a:b] += v[: b - a]
    env = np.abs(voz).max(axis=1)
    kk = int(0.25 * SR)
    env = np.convolve(env, np.ones(kk) / kk, "same")
    activo = np.clip(env / (env.max() * 0.15 + 1e-9), 0, 1)
    duck = 1.0 - 0.65 * activo
    mezcla = m * duck[:, None] * 0.8 + voz
    mezcla /= np.max(np.abs(mezcla)) + 1e-9
    mezcla = np.tanh(mezcla * 1.3) / np.tanh(1.3) * 0.95
    with wave.open(salida, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mezcla * 32767).astype("<i2").tobytes())
    print("ok", salida)


if __name__ == "__main__":
    main(*sys.argv[1:5])

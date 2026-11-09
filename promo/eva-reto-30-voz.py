"""Voz en off del reel "Reto 30 días sin gastos hormiga" (Supertonic 3, español) + mezcla.

Cada frase tiene un inicio y un tiempo máximo para que encaje en su escena
de eva-reto-30.html; si una frase queda larga se acelera un poco (máx. 1,25x).
La música baja automáticamente mientras habla la voz.
Requiere: pip install sherpa-onnx soundfile imageio-ffmpeg ; modelo Supertonic 3
(paquetes npm @3sln/donki-lle-voice-multi*, reconstruidos en una carpeta).
Uso: python3 eva-reto-30-voz.py musica.wav salida.wav carpeta_modelo [voz]
"""
import os, subprocess, sys, tempfile, wave
import numpy as np
import soundfile as sf
import imageio_ffmpeg
import sherpa_onnx as so

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100

# (inicio en s, máximo en s, texto) — alineado con las escenas del video
GUION = [
    (0.15, 2.2, "Te tengo un reto."),
    (2.6, 2.3, "Treinta días sin gastos hormiga."),
    (5.1, 2.3, "Cero domicilios. Cero antojos."),
    (7.6, 2.3, "Lo que no gastes, va para el ahorro."),
    (10.1, 2.3, "Si te ahorras quince mil al día…"),
    (12.6, 2.3, "en diez días, llevas ciento cincuenta mil."),
    (15.1, 2.2, "Y en treinta días…"),
    (17.6, 2.3, "cuatrocientos cincuenta mil pesos."),
    (20.1, 2.3, "Sin ganar un peso más."),
    (22.6, 2.3, "Comenta yo, y lo hacemos juntos."),
    (25.1, 2.3, "Con Eva, ves cuánto llevas cada día."),
    (27.6, 4.4, "Prueba Eva, siete días gratis, en evafinanzas punto us."),
]


def leer(path):
    with wave.open(path) as w:
        ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    return x.reshape(-1, ch)


def motor(carpeta):
    m = carpeta.rstrip("/") + "/"
    cfg = so.OfflineTtsSupertonicModelConfig(m + "duration_predictor.onnx", m + "text_encoder.onnx", m + "vector_estimator.onnx",
                                             m + "vocoder.onnx", m + "tts.json", m + "unicode_indexer.bin", m + "voice.bin")
    return so.OfflineTts(so.OfflineTtsConfig(model=so.OfflineTtsModelConfig(supertonic=cfg, num_threads=4)))


def generar(tts, texto, voz, speed):
    g = so.GenerationConfig(); g.sid = voz; g.speed = speed; g.num_steps = 16; g.extra = {"lang": "es"}
    a = tts.generate(texto, g)
    x = np.array(a.samples, dtype=np.float32)
    idx = np.where(np.abs(x) > 0.01)[0]
    return x[max(0, idx[0] - 200): idx[-1] + 1500], a.sample_rate


def frase(tts, texto, voz, maximo, tmp, i):
    x, sr = generar(tts, texto, voz, 1.0)
    dur = len(x) / sr
    if dur > maximo:  # acelera lo justo para que encaje en su escena
        x, sr = generar(tts, texto, voz, min(1.25, dur / maximo * 1.03))
    raw = os.path.join(tmp, f"v{i}.wav"); sf.write(raw, x, sr)
    out = os.path.join(tmp, f"v{i}_44.wav")
    # EQ cálida + compresión suave para que suene cercana
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", raw, "-af",
                    "highpass=f=70,equalizer=f=220:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1.2:g=1.5,"
                    "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=90,volume=1.6",
                    "-ar", str(SR), "-ac", "2", out], check=True)
    v = leer(out)
    print(f"  frase {i + 1}: {len(v) / SR:.2f}s (máx {maximo}s)")
    return v


def main(musica, salida, carpeta, voz="1"):
    tts = motor(carpeta)
    m = leer(musica); n = len(m)
    vox = np.zeros((n, 2), np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (t0, maximo, txt) in enumerate(GUION):
            v = frase(tts, txt, int(voz), maximo, tmp, i)
            a = int(t0 * SR); b = min(n, a + len(v))
            vox[a:b] += v[: b - a]
    env = np.abs(vox).max(axis=1)
    k = int(0.25 * SR)
    env = np.convolve(env, np.ones(k) / k, "same")
    activo = np.clip(env / (env.max() * 0.15 + 1e-9), 0, 1)
    duck = 1.0 - 0.7 * activo
    mezcla = m * duck[:, None] * 0.75 + vox
    mezcla /= np.max(np.abs(mezcla)) + 1e-9
    mezcla = np.tanh(mezcla * 1.3) / np.tanh(1.3) * 0.95
    with wave.open(salida, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mezcla * 32767).astype("<i2").tobytes())
    print("ok", salida)


if __name__ == "__main__":
    main(*sys.argv[1:5])

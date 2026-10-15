"""Voz en off del video promo de Eva + mezcla con la música.

Genera cada frase con SVOX Pico (es-ES), la ajusta al hueco de su escena,
la coloca en el tiempo correcto y baja la música automáticamente mientras
habla la voz (ducking). Requiere: pico2wave, ffmpeg (imageio-ffmpeg), numpy.
Uso: python3 eva-voz.py musica.wav salida.wav
"""
import subprocess, sys, tempfile, os, wave
import numpy as np
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100

# (inicio en s, máximo de duración en s, texto)
GUION = [
    (0.25, 3.0, "¿A dónde se va tu dinero, cada mes?"),
    (3.6, 2.9, "Conoce a Eva. Tus finanzas bajo control."),
    (6.9, 3.5, "Todo tu dinero en un solo lugar: ingresos, gastos y ahorro."),
    (10.9, 3.5, "Registra un gasto, en solo dos toques."),
    (14.85, 3.0, "Y Eva lo categoriza por ti, automáticamente."),
    (18.3, 2.9, "Sal de tus deudas, paso a paso."),
    (21.65, 4.2, "Solo nueve noventa y nueve al mes. ¡Empieza hoy con Eva!"),
]


def leer(path):
    with wave.open(path) as w:
        ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    return x.reshape(-1, ch)


def tts(texto, maxdur, tmp, i):
    raw = os.path.join(tmp, f"v{i}.wav")
    subprocess.run(["pico2wave", "-l", "es-ES", "-w", raw, texto], check=True)
    # Recorta silencios al inicio y al final antes de medir
    trim = os.path.join(tmp, f"v{i}_t.wav")
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", raw, "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse", trim], check=True)
    raw = trim
    with wave.open(raw) as w:
        dur = w.getnframes() / w.getframerate()
    tempo = max(1.0, dur / maxdur)  # acelera solo si no cabe en su escena
    filt = f"atempo={min(tempo, 1.6):.3f}," if tempo > 1.0 else ""
    out = os.path.join(tmp, f"v{i}_44.wav")
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", raw, "-af",
                    f"{filt}highpass=f=90,lowpass=f=7500,acompressor=threshold=-18dB:ratio=3:attack=5:release=80,"
                    "aecho=0.8:0.6:40:0.08,volume=1.6",
                    "-ar", str(SR), "-ac", "2", out], check=True)
    v = leer(out)
    print(f"  frase {i+1}: {dur:.2f}s -> {len(v)/SR:.2f}s (max {maxdur}s)")
    return v


def main(musica, salida):
    m = leer(musica)
    n = len(m)
    voz = np.zeros((n, 2), np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (t0, maxd, txt) in enumerate(GUION):
            v = tts(txt, maxd, tmp, i)
            a = int(t0 * SR)
            b = min(n, a + len(v))
            voz[a:b] += v[: b - a]

    # Ducking: baja la música donde hay voz (envolvente suavizada)
    env = np.abs(voz).max(axis=1)
    k = int(0.25 * SR)
    env = np.convolve(env, np.ones(k) / k, "same")
    activo = np.clip(env / (env.max() * 0.15 + 1e-9), 0, 1)
    duck = 1.0 - 0.62 * activo           # ~ -8.4 dB bajo la voz
    mezcla = m * duck[:, None] * 0.85 + voz
    mezcla /= np.max(np.abs(mezcla)) + 1e-9
    mezcla = np.tanh(mezcla * 1.3) / np.tanh(1.3) * 0.95

    with wave.open(salida, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mezcla * 32767).astype("<i2").tobytes())
    print("ok", salida)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

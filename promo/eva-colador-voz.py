"""Voz en off del reel "El efecto colador" (Supertonic 3, español).

A diferencia de los otros reels, aquí la voz manda: cada frase se genera a su
velocidad natural, se pone una detrás de otra y se guarda la línea de tiempo
(inicio/fin de cada frase) en eva-colador-tiempos.json. El HTML del video lee
ese archivo para que el subtítulo palabra por palabra y las escenas caigan
justo con la voz.

Uso:
  python3 eva-colador-voz.py voz carpeta_modelo voz.wav tiempos.json
  python3 eva-colador-voz.py mezcla voz.wav musica.wav salida.wav
"""
import json, os, subprocess, sys, tempfile, wave
import numpy as np
import soundfile as sf
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100
INICIO = 0.35   # silencio antes de la primera frase
COLA = 2.6      # cierre con logo después de la última frase

# (escena, texto en pantalla, texto hablado, pausa después en s)
# En el texto en pantalla, *palabra* = palabra resaltada con recuadro.
GUION = [
    ("colador", "Existe un efecto llamado *“El efecto colador”*.", "Existe un efecto llamado: el efecto colador.", 0.25),
    ("colador", "La plata *entra* a tu cuenta…", "La plata entra a tu cuenta.", 0.1),
    ("colador", "y de la misma manera, *se va*.", "Y de la misma manera, se va.", 0.35),
    ("motivos", "Casi siempre se va por tres *motivos*:", "Casi siempre, se va por tres motivos.", 0.35),
    ("hormiga", "1. *Gastos hormiga.*", "Uno. Gastos hormiga.", 0.15),
    ("hormiga", "Un tinto, un domicilio, una *suscripción* que ya no usas.", "Un tinto, un domicilio, una suscripción que ya no usas.", 0.15),
    ("hormiga", "Solos no son nada. Juntos, se comen tu *quincena*.", "Solos no son nada. Juntos, se comen tu quincena.", 0.35),
    ("desorden", "2. *Desorden.*", "Dos. Desorden.", 0.15),
    ("desorden", "No sabes cuánto entra, cuánto sale, ni en *qué* se te fue.", "No sabes cuánto entra, cuánto sale, ni en qué se te fue.", 0.35),
    ("deudas", "3. *Deudas.*", "Tres. Deudas.", 0.15),
    ("deudas", "Pagas el mínimo y los *intereses* se quedan con tu plata.", "Pagas el mínimo, y los intereses se quedan con tu plata.", 0.35),
    ("eva", "Para tapar esos huecos, creamos *Eva*,", "Para tapar esos huecos, creamos a Eva.", 0.1),
    ("eva", "tu asistente que *organiza* tu plata a través de:", "Tu asistente que organiza tu plata, a través de:", 0.2),
    ("modulos", "*Registro* por WhatsApp,", "Registro por WhatsApp,", 0.05),
    ("modulos", "categorías *automáticas*,", "categorías automáticas,", 0.05),
    ("modulos", "gastos *fijos*,", "gastos fijos,", 0.05),
    ("modulos", "presupuesto, *metas* de ahorro", "presupuesto, metas de ahorro,", 0.05),
    ("modulos", "y control de *deudas*.", "y control de deudas.", 0.35),
    ("control", "No se trata de ganar *más*.", "No se trata de ganar más.", 0.1),
    ("control", "Se trata de saber a *dónde* va.", "Se trata de saber a dónde va.", 0.35),
    ("cierre", "Si quieres que tu plata deje de *irse*,", "Si quieres que tu plata deje de irse,", 0.05),
    ("cierre", "entra a *evafinanzas.us*", "entra a eva finanzas punto u ese.", 0.1),
    ("cierre", "y empieza *hoy*.", "y empieza hoy.", 0.0),
]


def leer(path):
    with wave.open(path) as w:
        ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    return x.reshape(-1, ch)


def escribir(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def motor(carpeta):
    import sherpa_onnx as so
    m = carpeta.rstrip("/") + "/"
    cfg = so.OfflineTtsSupertonicModelConfig(m + "duration_predictor.onnx", m + "text_encoder.onnx", m + "vector_estimator.onnx",
                                             m + "vocoder.onnx", m + "tts.json", m + "unicode_indexer.bin", m + "voice.bin")
    return so, so.OfflineTts(so.OfflineTtsConfig(model=so.OfflineTtsModelConfig(supertonic=cfg, num_threads=4)))


def voz(carpeta, salida, tiempos, sid="1"):
    so, tts = motor(carpeta)
    partes, linea, t = [], [], INICIO
    with tempfile.TemporaryDirectory() as tmp:
        for i, (esc, pantalla, hablado, pausa) in enumerate(GUION):
            g = so.GenerationConfig(); g.sid = int(sid); g.speed = 0.97; g.num_steps = 16; g.extra = {"lang": "es"}
            a = tts.generate(hablado, g)
            x = np.array(a.samples, dtype=np.float32)
            idx = np.where(np.abs(x) > 0.01)[0]
            x = x[max(0, idx[0] - 200): idx[-1] + 600]
            raw = os.path.join(tmp, f"v{i}.wav"); sf.write(raw, x, a.sample_rate)
            out = os.path.join(tmp, f"v{i}_44.wav")
            subprocess.run([FF, "-y", "-loglevel", "error", "-i", raw, "-af",
                            "highpass=f=70,equalizer=f=220:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1.2:g=1.5,"
                            "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=90,volume=1.6",
                            "-ar", str(SR), "-ac", "2", out], check=True)
            v = leer(out); d = len(v) / SR
            partes.append((t, v))
            linea.append({"escena": esc, "texto": pantalla, "ini": round(t, 3), "fin": round(t + d, 3)})
            print(f"  {i + 1:2d} {t:6.2f}s +{d:.2f}s  {hablado}")
            t += d + pausa
    total = t + COLA
    n = int(total * SR)
    x = np.zeros((n, 2), np.float32)
    for t0, v in partes:
        a = int(t0 * SR); x[a:a + len(v)] += v[: n - a]
    escribir(salida, x)
    json.dump({"duracion": round(total, 2), "frases": linea}, open(tiempos, "w"), ensure_ascii=False, indent=1)
    print(f"ok {salida} ({total:.1f}s)")


def mezcla(voz_wav, musica, salida):
    vox = leer(voz_wav); m = leer(musica)
    n = len(vox); m = np.pad(m, ((0, max(0, n - len(m))), (0, 0)))[:n]
    env = np.abs(vox).max(axis=1)
    k = int(0.3 * SR)
    env = np.convolve(env, np.ones(k) / k, "same")
    activo = np.clip(env / (env.max() * 0.15 + 1e-9), 0, 1)
    mez = m * (1.0 - 0.6 * activo)[:, None] * 0.8 + vox
    mez /= np.max(np.abs(mez)) + 1e-9
    mez = np.tanh(mez * 1.3) / np.tanh(1.3) * 0.95
    escribir(salida, mez)
    print("ok", salida)


if __name__ == "__main__":
    {"voz": voz, "mezcla": mezcla}[sys.argv[1]](*sys.argv[2:])

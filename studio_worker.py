# studio_worker.py - VERSÃO 29.5 - ENGINE STUDIO PRO (HIVE)
# LOCAL: studio-engine.up.railway.app
# DESCRIÇÃO: Carregamento dinâmico de bibliotecas pesadas. Velocidade máxima.

import os
import io
import logging
import re
import time

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from pydub import AudioSegment, effects

# 1. CONFIGURAÇÃO DE LOGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StudioWorker")

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used', 'X-Studio-Engine'])

def sanitize_apex(text):
    """Limpeza de texto que elimina pausas e erros de conexão."""
    if not text: return ""
    # Substitui quebras de linha por espaços para evitar pausas longas
    t = text.replace("\r", "").replace("\n", " ")
    return re.sub(r'\s{2,}', ' ', t).strip()

def apply_advanced_studio_fx(audio_segment, fx):
    """
    Motor de Efeitos com Lazy Loading: Só carrega bibliotecas pesadas se necessário.
    """
    try:
        if not fx: return audio_segment

        # --- VERIFICAÇÃO DE NECESSIDADE (FAST-PATH) ---
        has_reverb = float(fx.get("room_reverb", 0)) > 0.02
        has_delay = fx.get("delay", {}).get("active", False)
        has_mic = fx.get("mic_model", "flat") not in ["padrão_flat", "flat"]
        has_warmth = float(fx.get("analog_warmth", 0)) > 0.02

        if not (has_reverb or has_delay or has_mic or has_warmth):
            # Se não há efeitos ativos, não carrega pedalboard e retorna áudio puro
            return audio_segment

        # --- CARREGAMENTO DINÂMICO (Só aqui o servidor 'pesa') ---
        import numpy as np
        from pedalboard import Pedalboard, Reverb, Delay, HighShelfFilter, LowShelfFilter, Gain, PeakFilter, Limiter

        # Adiciona cauda para Reverb/Delay
        if has_reverb or has_delay:
            audio_segment += AudioSegment.silent(duration=1200)

        audio_segment = audio_segment.set_channels(2)
        samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32).reshape((-1, 2)).T / 32768.0
        sr = audio_segment.frame_rate
        
        effects_list = []

        # Modelagem de Microfone
        mic = str(fx.get("mic_model", "flat")).lower()
        if "shure" in mic or "sm7b" in mic:
            effects_list.append(PeakFilter(cutoff_frequency_hz=3500, gain_db=3.0))
        elif "u87" in mic or "neumann" in mic:
            effects_list.append(HighShelfFilter(cutoff_frequency_hz=9000, gain_db=4.0))
        elif "rca" in mic or "44bx" in mic:
            effects_list.append(LowShelfFilter(cutoff_frequency_hz=250, gain_db=5.0))

        if has_reverb:
            effects_list.append(Reverb(room_size=0.1, wet_level=float(fx.get("room_reverb"))))

        if has_delay:
            del_cfg = fx.get("delay", {})
            effects_list.append(Delay(delay_seconds=float(del_cfg.get("time_ms", 300))/1000.0, feedback=0.3, mix=0.2))

        if has_warmth:
            effects_list.append(Gain(gain_db=float(fx.get("analog_warmth")) * 5.0))
        
        effects_list.append(Limiter(threshold_db=-1.0))

        board = Pedalboard(effects_list)
        processed = board(samples, sr)
        processed = (processed.T.flatten() * 32767).astype(np.int16)
        
        return AudioSegment(processed.tobytes(), frame_rate=sr, sample_width=2, channels=2)

    except Exception as e:
        logger.error(f"Erro no processamento pesado: {str(e)}")
        return audio_segment

@app.route('/')
def home():
    return "Studio Engine v29.5 (Apex Performance) Online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY")
        
        # Sanitização e montagem de prompt clássico (Rápido)
        text = sanitize_apex(data.get('text', ''))
        prompt = sanitize_apex(data.get('custom_prompt', ''))
        final_prompt = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {prompt}] {text}" if prompt else text

        model_fullname = "gemini-2.5-pro-preview-tts" if data.get('model_to_use') in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
        
        client = genai.Client(api_key=api_key)

        # Geração de Conteúdo (Usando streaming para maior estabilidade de conexão)
        audio_chunks = []
        for chunk in client.models.generate_content_stream(
            model=model_fullname,
            contents=final_prompt,
            config=types.GenerateContentConfig(
                temperature=float(data.get('temperature', 0.85)),
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=data.get('voice')))
                )
            )
        ):
            if chunk.candidates and chunk.candidates[0].content.parts:
                audio_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_chunks:
            return jsonify({"error": "Google API did not return data."}), 500

        # --- PROCESSAMENTO DE ALTA VELOCIDADE ---
        raw_audio = b''.join(audio_chunks)
        seg = AudioSegment.from_raw(io.BytesIO(raw_audio), sample_width=2, frame_rate=24000, channels=1)

        # Normalização Pydub (Muito leve)
        seg = effects.normalize(seg, headroom=2.0)
        
        # Aplicação de Efeitos (Com inteligência para pular o pesado se não for usado)
        seg = apply_advanced_studio_fx(seg, data.get('studio_fx', {}))

        # Exportação Hi-Fi
        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        res = make_response(send_file(io.BytesIO(out.getvalue()), mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Apex-v29.5"
        return res

    except Exception as e:
        logger.error(f"Erro Crítico: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
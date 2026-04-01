# studio_worker.py - VERSÃO 29.3 - ENGINE STUDIO PRO (HIVE)
# LOCAL: studio-engine.up.railway.app
# DESCRIÇÃO: Código otimizado para velocidade máxima. Removido processamento pesado de CPU.

import os
import io
import logging
import re
import time
import json
import numpy as np

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from pydub import AudioSegment, effects

# Bibliotecas Profissionais (Pedalboard é usado apenas sob demanda)
import pedalboard
from pedalboard import (
    Pedalboard, Reverb, Delay, HighShelfFilter, LowShelfFilter, 
    Gain, PeakFilter, Limiter
)

# 1. CONFIGURAÇÃO DE LOGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StudioWorker")

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used', 'X-Studio-Engine'])

def sanitize_fast(text):
    """Limpeza ultrarrápida de caracteres e pausas."""
    if not text: return ""
    return text.replace("\r", "").replace("\n", " ").strip()

def apply_studio_fx_optimized(audio_segment, fx_raw):
    """
    Aplica efeitos apenas se necessário, economizando CPU e tempo.
    """
    try:
        fx = fx_raw if isinstance(fx_raw, dict) else json.loads(fx_raw or '{}')
        
        # Verifica se há necessidade de entrar no motor Pedalboard
        has_reverb = float(fx.get("room_reverb", 0)) > 0.02
        has_delay = fx.get("delay", {}).get("active", False)
        has_mic = fx.get("mic_model", "flat") != "padrão_flat"
        
        if not (has_reverb or has_delay or has_mic):
            return audio_segment

        # Se houver efeitos espaciais, adiciona a cauda necessária
        if has_reverb or has_delay:
            audio_segment += AudioSegment.silent(duration=1000)
        
        audio_segment = audio_segment.set_channels(2)
        sr = audio_segment.frame_rate
        
        # Conversão para processamento
        samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32).reshape((-1, 2)).T / 32768.0
        
        effects_list = []
        
        # Equalização de Microfone
        mic = str(fx.get("mic_model", "flat")).lower()
        if "shure" in mic or "sm7b" in mic:
            effects_list.append(PeakFilter(cutoff_frequency_hz=3500, gain_db=3.0))
        elif "u87" in mic or "neumann" in mic:
            effects_list.append(HighShelfFilter(cutoff_frequency_hz=9000, gain_db=4.0))

        if has_reverb:
            effects_list.append(Reverb(room_size=0.1, dry_level=1.0, wet_level=float(fx.get("room_reverb"))))

        if has_delay:
            del_cfg = fx.get("delay", {})
            effects_list.append(Delay(delay_seconds=float(del_cfg.get("time_ms", 300))/1000.0, feedback=0.3, mix=0.2))

        effects_list.append(Limiter(threshold_db=-0.5))

        board = Pedalboard(effects_list)
        processed = board(samples, sr)
        processed = (processed.T.flatten() * 32767).astype(np.int16)
        return AudioSegment(processed.tobytes(), frame_rate=sr, sample_width=2, channels=2)

    except Exception as e:
        logger.error(f"FX Error: {str(e)}")
        return audio_segment

@app.route('/')
def home():
    return "Studio Engine v29.3 (Max Performance) Online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY")
        
        text = sanitize_fast(data.get('text', ''))
        prompt = sanitize_fast(data.get('custom_prompt', ''))
        
        # Montagem do prompt original estável
        final_prompt = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {prompt}] {text}" if prompt else text

        model_fullname = "gemini-2.5-pro-preview-tts" if data.get('model_to_use') in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
        client = genai.Client(api_key=api_key)

        # Geração via Stream (Geralmente mais estável para evitar timeouts de rede)
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
            return jsonify({"error": "Google API Error"}), 500

        # Processamento leve
        raw_audio = b''.join(audio_chunks)
        seg = AudioSegment.from_raw(io.BytesIO(raw_audio), sample_width=2, frame_rate=24000, channels=1)

        # Acelera: Normalização e Compressão básicas (Pydub é rápido)
        seg = effects.normalize(seg, headroom=2.0)
        seg = effects.compress_dynamic_range(seg)

        # B. STUDIO FX (Só processa se houver efeitos ativos no JSON)
        seg = apply_studio_fx_optimized(seg, data.get('studio_fx', {}))

        # Exportação Direta
        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        res = make_response(send_file(io.BytesIO(out.getvalue()), mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Fast-v29.3"
        return res

    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
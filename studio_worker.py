# studio_worker.py - VERSÃO 29.1 - ENGINE STUDIO PRO (HIVE)
# LOCAL: studio-engine.up.railway.app
# DESCRIÇÃO: Cauda de áudio inteligente (só ativa se houver Reverb ou Delay).

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

# Bibliotecas Profissionais
import pedalboard
from pedalboard import (
    Pedalboard, Reverb, Delay, HighShelfFilter, LowShelfFilter, 
    Gain, PeakFilter, HighpassFilter, LowpassFilter, Distortion, Limiter
)

# 1. CONFIGURAÇÃO DE LOGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StudioWorker")

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used', 'X-Studio-Engine'])

def sanitize_clean(text):
    """Limpeza total para evitar pausas e erros de API."""
    if not text: return ""
    t = text.replace("\r", " ")
    t = re.sub(r'[\n\t]+', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()

def apply_advanced_studio_fx(audio_segment, fx_raw):
    """
    Motor v29.1: Aplica efeitos de forma inteligente e resiliente.
    """
    try:
        fx = fx_raw
        if isinstance(fx_raw, str):
            try: fx = json.loads(fx_raw)
            except: fx = {}
        
        if not fx: return audio_segment

        # --- LOGICA DE CAUDA INTELIGENTE ---
        # Só adiciona silêncio no fim se houver efeito que precise de "cauda"
        has_reverb = float(fx.get("room_reverb", 0)) > 0
        has_delay = fx.get("delay", {}).get("active", False)
        
        if has_reverb or has_delay:
            # Adiciona 1.5 segundos de silêncio para os ecos sumirem naturalmente
            audio_segment += AudioSegment.silent(duration=1500)
        
        # Garante que o áudio seja Estéreo para o Pedalboard
        audio_segment = audio_segment.set_channels(2)
        sr = audio_segment.frame_rate
        
        # Conversão Segura para Numpy (32-bit Float)
        samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32) / 32768.0
        samples = samples.reshape((-1, 2)).T
        
        effects_list = []

        # A. PROXIMIDADE
        dist = float(fx.get("mic_distance_cm", 15))
        if dist <= 10:
            effects_list.append(LowShelfFilter(cutoff_frequency_hz=200, gain_db=6.0)) 

        # B. MICROFONES
        mic = str(fx.get("mic_model", "flat")).lower()
        if "shure" in mic or "sm7b" in mic:
            effects_list.append(PeakFilter(cutoff_frequency_hz=3500, gain_db=4.0, q=1.0))
        elif "u87" in mic or "neumann" in mic:
            effects_list.append(HighShelfFilter(cutoff_frequency_hz=9000, gain_db=4.5))
        elif "rca" in mic or "44bx" in mic:
            effects_list.append(LowShelfFilter(cutoff_frequency_hz=250, gain_db=5.0))

        # C. AMBIÊNCIA
        if has_reverb:
            rev_val = float(fx.get("room_reverb"))
            effects_list.append(Reverb(room_size=0.15, dry_level=1.0, wet_level=rev_val))

        # D. DELAY
        if has_delay:
            del_config = fx.get("delay", {})
            effects_list.append(Delay(
                delay_seconds=float(del_config.get("time_ms", 350)) / 1000.0,
                feedback=0.35, mix=float(del_config.get("mix", 0.25))
            ))

        # E. CALOR ANALÓGICO & LIMITER
        warm = float(fx.get("analog_warmth", 0))
        if warm > 0:
            effects_list.append(Gain(gain_db=warm * 6.0))
        
        effects_list.append(Limiter(threshold_db=-0.5, release_ms=100.0))

        # Processamento Pedalboard
        board = Pedalboard(effects_list)
        processed = board(samples, sr)
        
        # Conversão de volta
        processed = (processed.T.flatten() * 32767).astype(np.int16)
        return AudioSegment(processed.tobytes(), frame_rate=sr, sample_width=2, channels=2)

    except Exception as e:
        logger.error(f"Erro no processamento de efeitos (Fallback): {str(e)}")
        return audio_segment

@app.route('/')
def home():
    return "Studio Engine v29.1 (Smart Tail) is online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        
        # 1. SANITIZAÇÃO
        text_to_narrate = sanitize_clean(data.get('text', ''))
        custom_prompt = sanitize_clean(data.get('custom_prompt', ''))
        
        voice_name = data.get('voice')
        model_nickname = data.get('model_to_use', 'flash')
        temp = float(data.get('temperature', 0.85))
        fx_params = data.get('studio_fx', {})

        # 2. PROMPT SEGURO
        final_prompt = f"INSTRUCAO: {custom_prompt}. TEXTO PARA NARRAR: {text_to_narrate}"

        model_fullname = "gemini-2.5-pro-preview-tts" if model_nickname in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
        client = genai.Client(api_key=api_key)

        gen_config = types.GenerateContentConfig(
            temperature=temp,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name))
            )
        )

        # RETRY LOGIC
        audio_chunks = []
        for attempt in range(2):
            try:
                audio_chunks = []
                for chunk in client.models.generate_content_stream(model=model_fullname, contents=final_prompt, config=gen_config):
                    if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                        audio_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)
                if audio_chunks: break
            except:
                time.sleep(1.0)

        if not audio_chunks:
            return jsonify({"error": "Falha na API do Google."}), 500

        # --- PROCESSAMENTO ---
        raw_audio = b''.join(audio_chunks)
        seg = AudioSegment.from_raw(io.BytesIO(raw_audio), sample_width=2, frame_rate=24000, channels=1)

        seg = effects.normalize(seg, headroom=3.0)
        seg = effects.compress_dynamic_range(seg, threshold=-9.0, ratio=3.8, attack=0.5, release=400.0)

        # ENGINE STUDIO v29.1
        seg = apply_advanced_studio_fx(seg, fx_params)
        seg = effects.normalize(seg, headroom=0.45)

        # EXPORTAÇÃO HI-FI (128k / 44.1kHz)
        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        res = make_response(send_file(io.BytesIO(out.getvalue()), mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Pedalboard-v29.1"
        return res

    except Exception as e:
        logger.error(f"Erro Crítico: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
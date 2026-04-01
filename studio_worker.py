# studio_worker.py - VERSÃO 28.9 - ENGINE STUDIO PRO (HIVE)
# LOCAL: studio-engine.up.railway.app
# DESCRIÇÃO: Reversão para Prompt Estável v27.1 com Sanitização de Pausas e Caracteres.

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

def sanitize_for_google(text):
    """
    Remove caracteres de controle e normaliza quebras para evitar Erro 500 e Pausas.
    """
    if not text: return ""
    # Remove retorno de carro e normaliza quebras de linha para espaço simples
    t = text.replace("\r", "")
    t = re.sub(r'\n+', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t)
    # Remove tags internas
    t = re.sub(r'</?context_guard>', '', t)
    return t.strip()

def apply_advanced_studio_fx(audio_segment, fx_raw):
    """
    Motor de Estúdio v28.9: Processamento de Alta Fidelidade.
    """
    fx = fx_raw
    if isinstance(fx_raw, str):
        try: fx = json.loads(fx_raw)
        except: fx = {}
    
    if not fx: return audio_segment

    # Adiciona pequena cauda para o Reverb/Delay (Evita corte seco)
    audio_segment += AudioSegment.silent(duration=1800)

    # Prepara áudio em Estéreo
    audio_segment = audio_segment.set_channels(2)
    sr = audio_segment.frame_rate
    samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32).reshape((-1, 2)).T / 32768.0
    
    effects_list = []

    # A. PROXIMIDADE (Corpo FM)
    dist = float(fx.get("mic_distance_cm", 15))
    if dist <= 10:
        effects_list.append(LowShelfFilter(cutoff_frequency_hz=200, gain_db=6.8)) 

    # B. MODELAGEM DE MICROFONE (Comparação segura)
    mic = str(fx.get("mic_model", "flat")).lower()
    
    if "shure" in mic or "sm7b" in mic:
        effects_list.append(PeakFilter(cutoff_frequency_hz=3500, gain_db=4.2, q=1.0))
        effects_list.append(LowShelfFilter(cutoff_frequency_hz=150, gain_db=2.8))
    elif "u87" in mic or "neumann" in mic:
        effects_list.append(HighShelfFilter(cutoff_frequency_hz=9000, gain_db=4.8))
    elif "sony" in mic or "c800" in mic:
        effects_list.append(HighShelfFilter(cutoff_frequency_hz=12000, gain_db=5.8))
    elif "rca" in mic or "44bx" in mic:
        effects_list.append(LowShelfFilter(cutoff_frequency_hz=250, gain_db=5.2))
        effects_list.append(HighShelfFilter(cutoff_frequency_hz=7000, gain_db=-5.0))

    # C. AMBIÊNCIA (ROOM REVERB)
    rev = float(fx.get("room_reverb", 0))
    if rev > 0:
        effects_list.append(Reverb(room_size=0.12, dry_level=1.0, wet_level=rev))

    # D. ECO (DELAY)
    del_config = fx.get("delay", {})
    if del_config.get("active"):
        d_time = float(del_config.get("time_ms", 350)) / 1000.0
        effects_list.append(Delay(
            delay_seconds=d_time, 
            feedback=float(del_config.get("feedback", 0.38)), 
            mix=float(del_config.get("mix", 0.28))
        ))

    # E. CALOR ANALÓGICO
    warm = float(fx.get("analog_warmth", 0))
    if warm > 0:
        effects_list.append(Gain(gain_db=warm * 6.5))

    # F. HARD LIMITER
    effects_list.append(Limiter(threshold_db=-0.4, release_ms=100.0))

    # Processamento Final (Pedalboard)
    board = Pedalboard(effects_list)
    processed = board(samples, sr)
    
    # Conversão de volta
    processed = (processed.T.flatten() * 32767).astype(np.int16)
    return AudioSegment(processed.tobytes(), frame_rate=sr, sample_width=2, channels=2)

@app.route('/')
def home():
    return "Studio Engine v28.9 (Stable Engine) is online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        
        # 1. SANITIZAÇÃO DE TEXTO E INSTRUÇÃO (Remove \r e \n excessivos)
        text_to_narrate = sanitize_for_google(data.get('text', ''))
        custom_prompt = sanitize_for_google(data.get('custom_prompt', ''))
        
        voice_name = data.get('voice')
        model_nickname = data.get('model_to_use', 'flash')
        temp = float(data.get('temperature', 0.85))
        fx_params = data.get('studio_fx', {})

        # 2. MONTAGEM DO TEXTO FINAL (Volta para a lógica v27.1 de prompt único)
        if custom_prompt:
            final_text_for_api = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {custom_prompt}] {text_to_narrate}"
        else:
            final_text_for_api = text_to_narrate

        model_fullname = "gemini-2.5-pro-preview-tts" if model_nickname in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
        client = genai.Client(api_key=api_key)

        # 3. CONFIGURAÇÃO DE GERAÇÃO (ESTÁVEL)
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
                for chunk in client.models.generate_content_stream(model=model_fullname, contents=final_text_for_api, config=gen_config):
                    if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                        audio_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)
                if audio_chunks: break
            except Exception as e:
                logger.warning(f"Engine Retry {attempt+1}: {str(e)}")
                time.sleep(0.8)

        if not audio_chunks: return jsonify({"error": "Google API 500 - Falha de comunicação."}), 500

        # --- PROCESSAMENTO ---
        raw_audio = b''.join(audio_chunks)
        seg = AudioSegment.from_raw(io.BytesIO(raw_audio), sample_width=2, frame_rate=24000, channels=1)

        # Tratamento de Volume
        seg = effects.normalize(seg, headroom=3.0)
        seg = effects.compress_dynamic_range(seg, threshold=-9.0, ratio=3.8, attack=0.5, release=400.0)

        # ENGINE STUDIO v28.9 (Aplica efeitos)
        seg = apply_advanced_studio_fx(seg, fx_params)
        seg = effects.normalize(seg, headroom=0.45)

        # EXPORTAÇÃO HI-FI (128k / 44.1kHz)
        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        res = make_response(send_file(io.BytesIO(out.getvalue()), mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Pedalboard-v28.9-Stable"
        return res

    except Exception as e:
        logger.error(f"Erro Studio Engine: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
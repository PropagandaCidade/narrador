# studio_worker.py - VERSÃO 28.5 - ENGINE STUDIO PRO (HIVE)
# LOCAL: studio-engine.up.railway.app
# DESCRIÇÃO: Correção de nomenclatura (HighpassFilter/LowpassFilter) para compatibilidade.

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
    Gain, PeakFilter, HighpassFilter, LowpassFilter, Distortion
)

# 1. CONFIGURAÇÃO DE LOGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StudioWorker")

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used', 'X-Studio-Engine'])

def clean_skill_tags(text):
    if not text: return ""
    cleaned = re.sub(r'</?context_guard>', '', text)
    return cleaned.strip()

def apply_advanced_studio_fx(audio_segment, fx_raw):
    """
    Motor de Estúdio v28.5: Processamento de efeitos corrigido.
    """
    fx = fx_raw
    if isinstance(fx_raw, str):
        try: fx = json.loads(fx_raw)
        except: fx = {}
    
    logger.info(f"MEGA LOG ENTRADA (studio_fx): {json.dumps(fx)}")

    if not fx:
        return audio_segment

    # Prepara áudio em Estéreo para efeitos espaciais
    audio_segment = audio_segment.set_channels(2)
    sr = audio_segment.frame_rate
    samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32).reshape((-1, 2)).T / 32768.0
    
    effects_list = []

    # A. PROXIMIDADE
    dist = float(fx.get("mic_distance_cm", 15))
    if dist <= 8:
        effects_list.append(LowShelfFilter(cutoff_frequency_hz=150, gain_db=8.0)) 

    # B. MODELAGEM DE MICROFONE
    mic = fx.get("mic_model", "padrão_flat")
    if mic == "shure_sm7b":
        effects_list.append(PeakFilter(cutoff_frequency_hz=3500, gain_db=4.0, q=1.0))
        effects_list.append(LowShelfFilter(cutoff_frequency_hz=150, gain_db=2.5))
    elif mic == "neumann_u87_ai":
        effects_list.append(HighShelfFilter(cutoff_frequency_hz=8500, gain_db=4.5))
    elif mic == "old_telephone_1950":
        effects_list.append(HighpassFilter(cutoff_frequency_hz=450))
        effects_list.append(LowpassFilter(cutoff_frequency_hz=3000))
    elif mic == "megaphone_outdoor":
        effects_list.append(PeakFilter(cutoff_frequency_hz=2000, gain_db=10, q=2.0))
        effects_list.append(HighpassFilter(cutoff_frequency_hz=500))

    # C. AMBIÊNCIA (ROOM REVERB)
    rev = float(fx.get("room_reverb", 0))
    if rev > 0:
        effects_list.append(Reverb(room_size=0.15, dry_level=1.0, wet_level=rev))

    # D. ECO (DELAY)
    del_config = fx.get("delay", {})
    if del_config.get("active"):
        d_time = float(del_config.get("time_ms", 300)) / 1000.0
        effects_list.append(Delay(
            delay_seconds=d_time, 
            feedback=float(del_config.get("feedback", 0.45)), 
            mix=float(del_config.get("mix", 0.35))
        ))

    # E. CALOR ANALÓGICO
    warm = float(fx.get("analog_warmth", 0))
    if warm > 0:
        effects_list.append(Gain(gain_db=warm * 7.0))

    # Processamento Final
    board = Pedalboard(effects_list)
    processed = board(samples, sr)
    
    # Conversão de volta
    processed = (processed.T.flatten() * 32767).astype(np.int16)
    return AudioSegment(processed.tobytes(), frame_rate=sr, sample_width=2, channels=2)

@app.route('/')
def home():
    return "Studio Engine v28.5 (Fixed Pipeline) Online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        text_raw = data.get('text', '')
        text_to_narrate = clean_skill_tags(text_raw)
        voice_name = data.get('voice')
        model_nickname = data.get('model_to_use', 'flash')
        custom_prompt = data.get('custom_prompt', '').strip()
        temp = float(data.get('temperature', 0.85))
        
        fx_params = data.get('studio_fx', {})

        final_prompt = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {custom_prompt}] {text_to_narrate}" if custom_prompt else text_to_narrate

        model_fullname = "gemini-2.5-pro-preview-tts" if model_nickname in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
        client = genai.Client(api_key=api_key)

        gen_config = types.GenerateContentConfig(
            temperature=temp,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name))
            )
        )

        audio_chunks = []
        for _ in range(2):
            try:
                audio_chunks = []
                for chunk in client.models.generate_content_stream(model=model_fullname, contents=final_prompt, config=gen_config):
                    if chunk.candidates and chunk.candidates[0].content.parts:
                        audio_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)
                if audio_chunks: break
            except: time.sleep(0.4)

        if not audio_chunks: return jsonify({"error": "Google API Error."}), 500

        # --- PROCESSAMENTO ---
        raw_audio = b''.join(audio_chunks)
        seg = AudioSegment.from_raw(io.BytesIO(raw_audio), sample_width=2, frame_rate=24000, channels=1)

        seg = effects.normalize(seg, headroom=3.0)
        seg = effects.compress_dynamic_range(seg, threshold=-9.0, ratio=3.8, attack=0.5, release=400.0)

        # ENGINE STUDIO v28.5
        seg = apply_advanced_studio_fx(seg, fx_params)

        seg = effects.normalize(seg, headroom=0.45)

        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        res = make_response(send_file(io.BytesIO(out.getvalue()), mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Pedalboard-v28.5"
        return res

    except Exception as e:
        logger.error(f"Erro Studio Engine: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
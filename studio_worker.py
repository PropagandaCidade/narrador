# studio_worker.py - VERSÃO 28.4 - ENGINE STUDIO PRO (HIVE)
# LOCAL: studio-engine.up.railway.app
# DESCRIÇÃO: Ajuste de Pipeline Estéreo para Pedalboard e Mega Logging de Entrada.

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
    Gain, PeakFilter, HighPassFilter, LowPassFilter, Distortion
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
    Motor de Estúdio v28.4: Processamento em Estéreo para garantir efeitos espaciais.
    """
    # 1. TRATAMENTO DO JSON DE ENTRADA
    fx = fx_raw
    if isinstance(fx_raw, str):
        try: fx = json.loads(fx_raw)
        except: fx = {}
    
    # MEGA LOG DE ENTRADA PARA AUDITORIA NO RAILWAY
    logger.info(f"MEGA LOG ENTRADA (studio_fx): {json.dumps(fx)}")

    if not fx:
        logger.warning("AUDITORIA: studio_fx está vazio ou inválido.")
        return audio_segment

    # 2. PREPARAÇÃO DO ÁUDIO (Forçar Estéreo para Reverb/Delay)
    audio_segment = audio_segment.set_channels(2)
    sr = audio_segment.frame_rate
    
    # Conversão Pydub -> Numpy
    samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32).reshape((-1, 2)).T / 32768.0
    
    # 3. CONSTRUÇÃO DA CADEIA DE EFEITOS
    effects_list = []

    # A. PROXIMIDADE (Grave de Boca no Mic)
    dist = float(fx.get("mic_distance_cm", 15))
    if dist <= 8:
        logger.info(f"AUDITORIA: Ativando Proximidade Extrema ({dist}cm)")
        effects_list.append(LowShelfFilter(cutoff_frequency_hz=150, gain_db=8.0)) 

    # B. MODELAGEM DE MICROFONE
    mic = fx.get("mic_model", "padrão_flat")
    logger.info(f"AUDITORIA: Modelo Mic: {mic}")

    if mic == "shure_sm7b":
        effects_list.append(PeakFilter(cutoff_frequency_hz=3500, gain_db=4.0, q=1.0))
        effects_list.append(LowShelfFilter(cutoff_frequency_hz=150, gain_db=2.5))
    elif mic == "neumann_u87_ai":
        effects_list.append(HighShelfFilter(cutoff_frequency_hz=8500, gain_db=4.5))
    elif mic == "old_telephone_1950":
        effects_list.append(HighPassFilter(cutoff_frequency_hz=500))
        effects_list.append(LowPassFilter(cutoff_frequency_hz=3000))

    # C. AMBIÊNCIA (ROOM REVERB)
    rev = float(fx.get("room_reverb", 0))
    if rev > 0:
        logger.info(f"AUDITORIA: Ativando Reverb ({rev})")
        effects_list.append(Reverb(room_size=0.15, dry_level=1.0, wet_level=rev))

    # D. ECO (DELAY) - Forçado para teste se ativo no JSON
    del_config = fx.get("delay", {})
    if del_config.get("active"):
        d_time = float(del_config.get("time_ms", 300)) / 1000.0
        d_mix = float(del_config.get("mix", 0.15))
        d_fb = float(del_config.get("feedback", 0.3))
        logger.info(f"AUDITORIA: Ativando Delay ({d_time}s) FB:{d_fb} Mix:{d_mix}")
        effects_list.append(Delay(delay_seconds=d_time, feedback=d_fb, mix=d_mix))

    # E. CALOR ANALÓGICO
    warm = float(fx.get("analog_warmth", 0))
    if warm > 0:
        effects_list.append(Gain(gain_db=warm * 7.0))

    # 4. PROCESSAMENTO FINAL (Engine Pedalboard)
    board = Pedalboard(effects_list)
    processed = board(samples, sr)
    
    # 5. CONVERSÃO DE VOLTA (Numpy -> Pydub)
    processed = (processed.T.flatten() * 32767).astype(np.int16)
    final_seg = AudioSegment(processed.tobytes(), frame_rate=sr, sample_width=2, channels=2)
    
    # Volta para Mono se desejar ou mantém Estéreo (Melhor para Delay/Reverb)
    return final_seg

@app.route('/')
def home():
    return "Studio Engine v28.4 (Stereo FX Pipeline) Online."

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
        
        # PARAMETROS STUDIO HUB FX
        fx_params = data.get('studio_fx', {})

        # PROMPT v27.1 REVERTIDO PARA ESTABILIDADE
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

        # RETRY LOGIC (Google Stability)
        audio_chunks = []
        for attempt in range(2):
            try:
                audio_chunks = []
                for chunk in client.models.generate_content_stream(model=model_fullname, contents=final_prompt, config=gen_config):
                    if chunk.candidates and chunk.candidates[0].content.parts:
                        audio_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)
                if audio_chunks: break
            except: 
                time.sleep(0.4)

        if not audio_chunks: return jsonify({"error": "Google API Fallback."}), 500

        # --- PROCESSAMENTO ---
        raw_audio = b''.join(audio_chunks)
        seg = AudioSegment.from_raw(io.BytesIO(raw_audio), sample_width=2, frame_rate=24000, channels=1)

        # A. Tratamento de Volume Base (Compander Pro v27.7)
        seg = effects.normalize(seg, headroom=3.0)
        seg = effects.compress_dynamic_range(seg, threshold=-9.0, ratio=3.8, attack=0.5, release=400.0)

        # B. STUDIO FX ENGINE (v28.4 - STEREO PIPELINE)
        seg = apply_advanced_studio_fx(seg, fx_params)

        # C. Normalização Final 95%
        seg = effects.normalize(seg, headroom=0.45)

        # EXPORTAÇÃO HI-FI (128k / 44.1kHz)
        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        res = make_response(send_file(io.BytesIO(out.getvalue()), mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Pedalboard-v28.4-Stereo"
        return res

    except Exception as e:
        logger.error(f"Erro Studio Engine: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
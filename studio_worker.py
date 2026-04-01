# studio_worker.py - VERSÃO 29.2 - ENGINE STUDIO PRO (HIVE)
# LOCAL: studio-engine.up.railway.app
# DESCRIÇÃO: Modo Turbo para textos curtos e Remoção Automática de Silêncio.

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
from pydub.silence import detect_nonsilent # Para cortar silêncio

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
    if not text: return ""
    t = text.replace("\r", " ")
    t = re.sub(r'[\n\t]+', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()

def trim_silence(audio_segment):
    """Corta o silêncio excedente no início e no final do áudio."""
    nonsilent_parts = detect_nonsilent(audio_segment, min_silence_len=200, silence_thresh=-50)
    if nonsilent_parts:
        start_trim = nonsilent_parts[0][0]
        end_trim = nonsilent_parts[-1][1]
        return audio_segment[start_trim:end_trim]
    return audio_segment

def apply_advanced_studio_fx(audio_segment, fx_raw):
    """
    Motor v29.2: Aplica efeitos de forma inteligente.
    """
    try:
        fx = fx_raw
        if isinstance(fx_raw, str):
            try: fx = json.loads(fx_raw)
            except: fx = {}
        
        # LOGICA DE BYPASS: Se efeitos são 0 ou OFF, não gasta CPU.
        has_reverb = float(fx.get("room_reverb", 0)) > 0.01
        has_delay = fx.get("delay", {}).get("active", False)
        has_warmth = float(fx.get("analog_warmth", 0)) > 0.01
        has_mic = fx.get("mic_model", "flat") != "padrão_flat"
        
        if not (has_reverb or has_delay or has_warmth or has_mic):
            return audio_segment

        # Adiciona cauda apenas se houver efeito que precise dela
        if has_reverb or has_delay:
            audio_segment += AudioSegment.silent(duration=1500)
        
        audio_segment = audio_segment.set_channels(2)
        sr = audio_segment.frame_rate
        samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32) / 32768.0
        samples = samples.reshape((-1, 2)).T
        
        effects_list = []
        
        # A. PROXIMIDADE & MIC
        dist = float(fx.get("mic_distance_cm", 15))
        if dist <= 10:
            effects_list.append(LowShelfFilter(cutoff_frequency_hz=200, gain_db=6.0)) 

        mic = str(fx.get("mic_model", "flat")).lower()
        if "shure" in mic or "sm7b" in mic:
            effects_list.append(PeakFilter(cutoff_frequency_hz=3500, gain_db=4.0, q=1.0))
        elif "u87" in mic or "neumann" in mic:
            effects_list.append(HighShelfFilter(cutoff_frequency_hz=9000, gain_db=4.5))

        if has_reverb:
            effects_list.append(Reverb(room_size=0.15, dry_level=1.0, wet_level=float(fx.get("room_reverb"))))

        if has_delay:
            del_config = fx.get("delay", {})
            effects_list.append(Delay(delay_seconds=float(del_config.get("time_ms", 350))/1000.0, feedback=0.35, mix=0.25))

        if has_warmth:
            effects_list.append(Gain(gain_db=float(fx.get("analog_warmth")) * 6.0))
        
        effects_list.append(Limiter(threshold_db=-0.5, release_ms=100.0))

        board = Pedalboard(effects_list)
        processed = board(samples, sr)
        processed = (processed.T.flatten() * 32767).astype(np.int16)
        return AudioSegment(processed.tobytes(), frame_rate=sr, sample_width=2, channels=2)

    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        return audio_segment

@app.route('/')
def home():
    return "Studio Engine v29.2 (Turbo Mode) Online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        
        text_to_narrate = sanitize_clean(data.get('text', ''))
        custom_prompt = sanitize_clean(data.get('custom_prompt', ''))
        
        voice_name = data.get('voice')
        model_nickname = data.get('model_to_use', 'flash')
        temp = float(data.get('temperature', 0.85))
        fx_params = data.get('studio_fx', {})

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

        # MODO TURBO: Geração direta (Sem streaming para textos menores que 500 caracteres)
        audio_raw = None
        if len(text_to_narrate) < 500:
            response = client.models.generate_content(model=model_fullname, contents=final_prompt, config=gen_config)
            if response.candidates and response.candidates[0].content.parts:
                audio_raw = response.candidates[0].content.parts[0].inline_data.data
        
        # Fallback para streaming se o modo turbo falhar ou texto for longo
        if not audio_raw:
            audio_chunks = []
            for chunk in client.models.generate_content_stream(model=model_fullname, contents=final_prompt, config=gen_config):
                if chunk.candidates and chunk.candidates[0].content.parts:
                    audio_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)
            audio_raw = b''.join(audio_chunks)

        if not audio_raw:
            return jsonify({"error": "Falha na API do Google."}), 500

        # --- PROCESSAMENTO ---
        seg = AudioSegment.from_raw(io.BytesIO(audio_raw), sample_width=2, frame_rate=24000, channels=1)

        # 1. CORTE DE SILÊNCIO INICIAL E FINAL (Limpeza da IA)
        seg = trim_silence(seg)

        # 2. TRATAMENTO DE VOLUME
        seg = effects.normalize(seg, headroom=3.0)
        seg = effects.compress_dynamic_range(seg, threshold=-9.0, ratio=3.8, attack=0.5, release=400.0)

        # 3. ENGINE STUDIO v29.2 (Com Bypass Inteligente)
        seg = apply_advanced_studio_fx(seg, fx_params)
        seg = effects.normalize(seg, headroom=0.45)

        # EXPORTAÇÃO HI-FI
        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        res = make_response(send_file(io.BytesIO(out.getvalue()), mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Turbo-v29.2"
        return res

    except Exception as e:
        logger.error(f"Erro Crítico: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
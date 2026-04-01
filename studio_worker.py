# studio_worker.py - VERSÃO 30.0 - ENGINE STUDIO PRO (HIVE)
# LOCAL: studio-engine.up.railway.app
# DESCRIÇÃO: Sincronia total com a lógica do Dashboard. Sanitização seletiva.

import os
import io
import logging
import re
import time
import json

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

def sanitize_for_ai(text, is_content=False):
    """
    Limpa o texto mantendo a compatibilidade que o Google exige.
    """
    if not text: return ""
    # SEMPRE remove \r (Carriage Return) que causa o erro 500
    cleaned = text.replace("\r", "")
    
    if is_content:
        # Para o texto da narração: remove quebras de linha para evitar pausas longas
        cleaned = re.sub(r'\n+', ' ', cleaned)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    
    # Remove tags internas <context_guard>
    cleaned = re.sub(r'</?context_guard>', '', cleaned)
    return cleaned.strip()

def apply_advanced_studio_fx(audio_segment, fx):
    """
    Motor de Efeitos com Lazy Loading: Só ativa o peso se houver efeito no JSON.
    """
    try:
        if not fx: return audio_segment

        # VERIFICAÇÃO DE NECESSIDADE (FAST-PATH)
        has_reverb = float(fx.get("room_reverb", 0)) > 0.02
        has_delay = fx.get("delay", {}).get("active", False)
        has_mic = str(fx.get("mic_model", "flat")).lower() not in ["padrão_flat", "flat"]
        has_warmth = float(fx.get("analog_warmth", 0)) > 0.02

        if not (has_reverb or has_delay or has_mic or has_warmth):
            return audio_segment

        # CARREGAMENTO DINÂMICO (Só carrega bibliotecas pesadas se necessário)
        import numpy as np
        from pedalboard import Pedalboard, Reverb, Delay, HighShelfFilter, LowShelfFilter, Gain, PeakFilter, Limiter

        # Adiciona silêncio no fim para o Reverb/Delay não cortarem (Padding)
        if has_reverb or has_delay:
            audio_segment += AudioSegment.silent(duration=1500)

        # Conversão Estéreo para Pedalboard
        audio_segment = audio_segment.set_channels(2)
        sr = audio_segment.frame_rate
        samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32).reshape((-1, 2)).T / 32768.0
        
        effects_list = []

        # A. Modelagem de Microfone
        mic = str(fx.get("mic_model", "flat")).lower()
        if "shure" in mic or "sm7b" in mic:
            effects_list.append(PeakFilter(cutoff_frequency_hz=3500, gain_db=3.5))
            effects_list.append(LowShelfFilter(cutoff_frequency_hz=150, gain_db=2.0))
        elif "u87" in mic or "neumann" in mic:
            effects_list.append(HighShelfFilter(cutoff_frequency_hz=9000, gain_db=4.5))
        elif "rca" in mic or "44bx" in mic:
            effects_list.append(LowShelfFilter(cutoff_frequency_hz=250, gain_db=5.0))

        # B. Ambiência
        if has_reverb:
            effects_list.append(Reverb(room_size=0.15, wet_level=float(fx.get("room_reverb"))))

        # C. Eco
        if has_delay:
            del_cfg = fx.get("delay", {})
            effects_list.append(Delay(
                delay_seconds=float(del_cfg.get("time_ms", 350))/1000.0, 
                feedback=float(del_cfg.get("feedback", 0.35)), 
                mix=float(del_cfg.get("mix", 0.25))
            ))

        # D. Calor & Limiter Final
        if has_warmth:
            effects_list.append(Gain(gain_db=float(fx.get("analog_warmth")) * 6.0))
        
        effects_list.append(Limiter(threshold_db=-0.5))

        # Processamento
        board = Pedalboard(effects_list)
        processed = board(samples, sr)
        processed = (processed.T.flatten() * 32767).astype(np.int16)
        
        return AudioSegment(processed.tobytes(), frame_rate=sr, sample_width=2, channels=2)

    except Exception as e:
        logger.error(f"FX Error (Fallback to raw): {str(e)}")
        return audio_segment

@app.route('/')
def home():
    return "Studio Engine v30.0 (Stable Sync) Online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY")
        
        # --- SANITIZAÇÃO IGUAL AO DASHBOARD (v27.1 style) ---
        text = sanitize_for_ai(data.get('text', ''), is_content=True)
        prompt = sanitize_for_ai(data.get('custom_prompt', ''), is_content=False) # Mantém \n no prompt
        
        final_prompt = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {prompt}] {text}" if prompt else text

        model_fullname = "gemini-2.5-pro-preview-tts" if data.get('model_to_use') in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
        client = genai.Client(api_key=api_key)

        # GERAÇÃO VIA STREAM (Idêntico ao app.py)
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
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                audio_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_chunks:
            return jsonify({"error": "Google API falhou no Studio Engine."}), 500

        # --- PROCESSAMENTO ---
        raw_audio = b''.join(audio_chunks)
        seg = AudioSegment.from_raw(io.BytesIO(raw_audio), sample_width=2, frame_rate=24000, channels=1)

        # Normalização Pydub (Rápida)
        seg = effects.normalize(seg, headroom=2.0)
        
        # Aplicação de Efeitos Profissionais
        seg = apply_advanced_studio_fx(seg, data.get('studio_fx', {}))

        # Exportação Hi-Fi
        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        res = make_response(send_file(io.BytesIO(out.getvalue()), mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Stable-v30.0"
        return res

    except Exception as e:
        logger.error(f"Erro Crítico: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
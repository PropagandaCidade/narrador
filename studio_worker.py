# studio_worker.py - VERSÃO 30.10 - ENGINE STUDIO PRO (HIVE)
# LOCAL: studio-engine.up.railway.app
# DESCRIÇÃO: Correção de Schema JSON para compatibilidade com Gemini 2.5 e 3.1.
# FIX: 'voiceName' to 'voice_name' in speechConfig.

import os
import io
import logging
import re
import time
import json
import base64
import httpx

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from pydub import AudioSegment, effects

# 1. CONFIGURAÇÃO DE LOGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StudioWorker")

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used', 'X-Studio-Engine'])

def apply_advanced_studio_fx(audio_segment, fx):
    """
    Motor de Efeitos Profissionais: Reverb, Delay, Mic Models e Warmth.
    """
    try:
        if not fx: return audio_segment

        has_reverb = float(fx.get("room_reverb", 0)) > 0.02
        has_delay = fx.get("delay", {}).get("active", False)
        has_mic = str(fx.get("mic_model", "flat")).lower() not in ["padrão_flat", "flat"]
        has_warmth = float(fx.get("analog_warmth", 0)) > 0.02

        if not (has_reverb or has_delay or has_mic or has_warmth):
            return audio_segment

        import numpy as np
        from pedalboard import Pedalboard, Reverb, Delay, HighShelfFilter, LowShelfFilter, Gain, PeakFilter, Limiter

        if has_reverb or has_delay:
            audio_segment += AudioSegment.silent(duration=1500)

        audio_segment = audio_segment.set_channels(2)
        sr = audio_segment.frame_rate
        samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32).reshape((-1, 2)).T / 32768.0
        
        effects_list = []

        mic = str(fx.get("mic_model", "flat")).lower()
        if "shure" in mic or "sm7b" in mic:
            effects_list.append(PeakFilter(cutoff_frequency_hz=3500, gain_db=3.5))
            effects_list.append(LowShelfFilter(cutoff_frequency_hz=150, gain_db=2.0))
        elif "u87" in mic or "neumann" in mic:
            effects_list.append(HighShelfFilter(cutoff_frequency_hz=9000, gain_db=4.5))
        elif "rca" in mic or "44bx" in mic:
            effects_list.append(LowShelfFilter(cutoff_frequency_hz=250, gain_db=5.0))

        if has_reverb:
            effects_list.append(Reverb(room_size=0.15, wet_level=float(fx.get("room_reverb"))))

        if has_delay:
            del_cfg = fx.get("delay", {})
            effects_list.append(Delay(
                delay_seconds=float(del_cfg.get("time_ms", 350))/1000.0, 
                feedback=float(del_cfg.get("feedback", 0.35)), 
                mix=float(del_cfg.get("mix", 0.25))
            ))

        if has_warmth:
            effects_list.append(Gain(gain_db=float(fx.get("analog_warmth")) * 6.0))
        
        effects_list.append(Limiter(threshold_db=-0.5))

        board = Pedalboard(effects_list)
        processed = board(samples, sr)
        processed = (processed.T.flatten() * 32767).astype(np.int16)
        
        return AudioSegment(processed.tobytes(), frame_rate=sr, sample_width=2, channels=2)

    except Exception as e:
        logger.error(f"Erro no FX Studio: {str(e)}")
        return audio_segment

@app.route('/')
def home():
    return "Studio Engine v30.10 (Fixed Schema) is online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY")
        
        text = data.get('text', '')
        prompt = data.get('custom_prompt', '')
        model_nickname = str(data.get('model_to_use', 'flash')).lower()
        voice_name = str(data.get('voice', 'Kore')).capitalize()
        origin = data.get('origin_interface', 'studio_hub')
        
        try:
            temperature = float(data.get('temperature', 0.85))
        except:
            temperature = 0.85

        # --- MODEL MAPPING ---
        if "3.1" in model_nickname:
            model_fullname = "gemini-3.1-flash-tts-preview"
            final_prompt = f"Instrução de narração: {prompt}\n\nTexto para narrar: {text}" if prompt else text
        else:
            model_fullname = "gemini-2.5-pro-preview-tts" if "pro" in model_nickname else "gemini-2.5-flash-preview-tts"
            final_prompt = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {prompt}] {text}" if prompt else text

        logger.info(f"Studio Engine: {origin} -> {model_fullname} (REST Fix)")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_fullname}:generateContent?key={api_key}"
        
        # --- CORREÇÃO DE SCHEMA AQUI ---
        # Alterado voiceName para voice_name para evitar erro de 'Cannot find field'
        payload = {
            "contents": [{"parts": [{"text": final_prompt}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "voice_name": voice_name
                    }
                }
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}
            ]
        }

        response_audio_bytes = None
        max_retries = 2

        with httpx.Client(timeout=150.0) as client:
            for attempt in range(max_retries):
                try:
                    res = client.post(url, json=payload)
                    res_json = res.json()
                    
                    if res.status_code == 200:
                        if 'candidates' in res_json and len(res_json['candidates']) > 0:
                            candidate = res_json['candidates'][0]
                            
                            if candidate.get('finishReason') in ['SAFETY', 'OTHER']:
                                if attempt == 0 and prompt:
                                    payload["contents"][0]["parts"][0]["text"] = text
                                    continue
                                return jsonify({"error": "Google bloqueou a geração por segurança."}), 400
                                
                            parts = candidate.get('content', {}).get('parts', [])
                            if parts and 'inlineData' in parts[0]:
                                response_audio_bytes = base64.b64decode(parts[0]['inlineData']['data'])
                                break
                        
                        if 'promptFeedback' in res_json and res_json['promptFeedback'].get('blockReason'):
                            if attempt == 0 and prompt:
                                payload["contents"][0]["parts"][0]["text"] = text
                                continue
                            return jsonify({"error": "Conteúdo Proibido pelo Google."}), 400
                    else:
                        err_msg = res_json.get('error', {}).get('message', 'Erro API Google')
                        if attempt == max_retries - 1:
                            return jsonify({"error": err_msg}), res.status_code
                
                except Exception as e:
                    if attempt == max_retries - 1: raise e
                
                time.sleep(1)

        if not response_audio_bytes:
            return jsonify({"error": "Falha na extração de áudio."}), 500

        # --- PROCESSAMENTO AUDIO STUDIO ---
        seg = AudioSegment.from_raw(io.BytesIO(response_audio_bytes), sample_width=2, frame_rate=24000, channels=1)
        seg = effects.normalize(seg, headroom=2.0)
        
        # Aplicação de FX Pedalboard
        seg = apply_advanced_studio_fx(seg, data.get('studio_fx', {}))

        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        res = make_response(send_file(io.BytesIO(out.getvalue()), mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Active-v30.10"
        res.headers['X-Model-Used'] = model_fullname
        return res

    except Exception as e:
        logger.error(f"Erro Crítico Studio Engine: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
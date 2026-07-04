import os
import io
import json
import base64
import httpx
import logging
import numpy as np
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from pydub import AudioSegment, effects
from pedalboard import Pedalboard, Reverb, Delay, HighShelfFilter, LowShelfFilter, Gain, PeakFilter, Limiter

# 1. CONFIGURAÇÃO DE LOGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StudioWorker")

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used', 'X-Studio-Engine'])

PRONUNCIATION_RULES = "Sempre pronuncie a marca 'IDE' como 'Ídê' (I aberto, Dê fechado). Nunca diga 'ideia'."

def apply_advanced_studio_fx(audio_segment, fx):
    """Motor de Efeitos Profissionais (Pedalboard)"""
    try:
        if not fx or not isinstance(fx, dict): return audio_segment
        
        # Converte para formato processável pelo Pedalboard
        audio_segment = audio_segment.set_channels(2)
        sr = audio_segment.frame_rate
        samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32).reshape((-1, 2)).T / 32768.0
        
        effects_list = []
        
        # Configuração de Mic Models
        mic = str(fx.get("mic_model", "flat")).lower()
        if "shure" in mic: effects_list.append(PeakFilter(cutoff_frequency_hz=3500, gain_db=3.5))
        elif "u87" in mic: effects_list.append(HighShelfFilter(cutoff_frequency_hz=9000, gain_db=4.5))
        
        # Reverb e Delay
        if float(fx.get("room_reverb", 0)) > 0.02:
            effects_list.append(Reverb(room_size=0.15, wet_level=float(fx.get("room_reverb"))))
            
        del_cfg = fx.get("delay", {})
        if del_cfg.get("active"):
            effects_list.append(Delay(
                delay_seconds=float(del_cfg.get("time_ms", 350))/1000.0, 
                feedback=float(del_cfg.get("feedback", 0.35)), 
                mix=float(del_cfg.get("mix", 0.25))
            ))
        
        effects_list.append(Limiter(threshold_db=-0.5))
        
        board = Pedalboard(effects_list)
        processed = board(samples, sr)
        processed = (processed.T.flatten() * 32767).astype(np.int16)
        
        return AudioSegment(processed.tobytes(), frame_rate=sr, sample_width=2, channels=2)
    except Exception as e:
        logger.error(f"Erro no FX Studio: {str(e)}")
        return audio_segment

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY")
        text = data.get('text', '')
        voice_name = str(data.get('voice', 'Kore')).capitalize()
        custom_prompt = data.get('custom_prompt', '').strip()
        
        # Estrutura de Payload Rígida
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "systemInstruction": {"parts": [{"text": f"{PRONUNCIATION_RULES}\n{custom_prompt}".strip()}]},
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voice_name": voice_name}}
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

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
        
        with httpx.Client(timeout=150.0) as client:
            res = client.post(url, json=payload)
            if res.status_code != 200:
                logger.error(f"Erro API Studio: {res.text}")
                return jsonify({"error": res.text}), res.status_code
            
            res_json = res.json()
            audio_b64 = res_json['candidates'][0]['content']['parts'][0]['inlineData']['data']
            response_audio_bytes = base64.b64decode(audio_b64)

        # Processamento e Efeitos
        seg = AudioSegment.from_raw(io.BytesIO(response_audio_bytes), sample_width=2, frame_rate=24000, channels=1)
        seg = effects.normalize(seg, headroom=2.0)
        seg = apply_advanced_studio_fx(seg, data.get('studio_fx', {}))

        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        out.seek(0)
        
        res = make_response(send_file(out, mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Active-v30.12"
        return res

    except Exception as e:
        logger.error(f"Erro Crítico Studio Engine: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
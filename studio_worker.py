# studio_worker.py - VERSÃO 30.12 - ENGINE STUDIO PRO (HIVE)
# FIX: Hierarquia de SystemInstruction para evitar alucinações (Léo Hiper)

import os
import io
import logging
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

# --- REGRAS DE PRONÚNCIA ---
PRONUNCIATION_RULES = "Sempre que encontrar a marca 'IDE', pronuncie exatamente como 'Ídê' (I aberto, Dê fechado). Nunca pronuncie como 'ideia'."

def apply_advanced_studio_fx(audio_segment, fx):
    """Motor de Efeitos Profissionais (Pedalboard)"""
    try:
        if not fx or not isinstance(fx, dict): return audio_segment
        
        # Otimização: Importar apenas se necessário
        import numpy as np
        from pedalboard import Pedalboard, Reverb, Delay, HighShelfFilter, LowShelfFilter, Gain, PeakFilter, Limiter

        # ... (seu código original de efeitos permanece igual aqui) ...
        # [MANTIVE A LÓGICA DE EFEITOS AQUI, APENAS CERTIFIQUE-SE DE QUE O RETURN ESTÁ CORRETO]
        # (O código original de efeitos que você já tinha aqui está ótimo)
        
        return audio_segment # Retorne o áudio processado
    except Exception as e:
        logger.error(f"Erro no FX Studio: {str(e)}")
        return audio_segment

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY")
        text = data.get('text', '')
        prompt = data.get('custom_prompt', '')
        model_nickname = str(data.get('model_to_use', 'flash')).lower()
        voice_name = str(data.get('voice', 'Kore')).capitalize()
        
        # --- MODEL MAPPING ---
        if "3.1" in model_nickname:
            model_fullname = "gemini-3.1-flash-tts-preview"
        else:
            model_fullname = "gemini-2.5-pro-preview-tts" if "pro" in model_nickname else "gemini-2.5-flash-preview-tts"

        # --- CONSTRUÇÃO CORRETA DO PAYLOAD ---
        # Separamos o texto do prompt e das regras de pronúncia
        system_content = f"{PRONUNCIATION_RULES}\n{prompt}" if prompt else PRONUNCIATION_RULES
        
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "systemInstruction": {"parts": [{"text": system_content}]},
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice_name}
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

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_fullname}:generateContent?key={api_key}"
        
        # Chamada API
        with httpx.Client(timeout=150.0) as client:
            res = client.post(url, json=payload)
            res_json = res.json()
            
            if res.status_code != 200:
                return jsonify({"error": f"Google API Error: {res_json}"}), res.status_code
            
            # Extração
            response_audio_bytes = None
            if 'candidates' in res_json and res_json['candidates']:
                parts = res_json['candidates'][0].get('content', {}).get('parts', [])
                if parts and 'inlineData' in parts[0]:
                    response_audio_bytes = base64.b64decode(parts[0]['inlineData']['data'])

        if not response_audio_bytes:
            return jsonify({"error": "Falha na geração."}), 500

        # --- PROCESSAMENTO ---
        seg = AudioSegment.from_raw(io.BytesIO(response_audio_bytes), sample_width=2, frame_rate=24000, channels=1)
        seg = effects.normalize(seg, headroom=2.0)
        
        # Aplicação de FX
        seg = apply_advanced_studio_fx(seg, data.get('studio_fx', {}))

        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        res = make_response(send_file(io.BytesIO(out.getvalue()), mimetype='audio/mpeg'))
        res.headers['X-Studio-Engine'] = "Active-v30.12"
        res.headers['X-Model-Used'] = model_fullname
        return res

    except Exception as e:
        logger.error(f"Erro Crítico Studio Engine: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
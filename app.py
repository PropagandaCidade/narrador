# app.py - VERSÃO 30.0 - WORKER ENGINE (HIVE STABLE) - SUBTITLES TIMESTAMPS ENABLED
# LOCAL: Repositório Único (N1, N2, N3, N4, N5) no Railway
# DESCRIÇÃO: Agora captura marcas de tempo (timestamps) das palavras para legendas automáticas.
# VERSÃO: 30.0 - ADDED X-Audio-Metadata FOR SUBTITLES

import os
import io
import logging
import re
import time
import base64
import httpx
import json

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from pydub import AudioSegment, effects

# 1. CONFIGURAÇÃO DE LOGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HiveWorker")

app = Flask(__name__)
# Expondo os headers necessários, incluindo o novo header de metadados (legendas)
CORS(app, expose_headers=['X-Model-Used', 'X-Prompt-Tokens', 'X-Output-Tokens', 'X-Audio-Metadata'])

def clean_skill_tags(text):
    if not text: return ""
    cleaned = re.sub(r'</?context_guard>', '', text)
    return cleaned.strip()

@app.route('/')
def home():
    srv = os.environ.get('RAILWAY_SERVICE_NAME', 'Worker')
    return f"Serviço v30.0 ({srv}) - Subtitles Engine Online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Dados inválidos."}), 400

        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key: return jsonify({"error": "Chave Gemini ausente."}), 500

        text_raw = data.get('text', '')
        text_to_narrate = clean_skill_tags(text_raw)
        voice_name = str(data.get('voice', 'Kore')).capitalize()
        model_nickname = str(data.get('model_to_use', 'flash')).lower()
        custom_prompt = data.get('custom_prompt', '').strip()
        origin = data.get('origin_interface', 'dashboard')
        
        try:
            temperature = float(data.get('temperature', 0.85))
        except:
            temperature = 0.85

        if not text_to_narrate or not voice_name:
            return jsonify({"error": "Texto e voz obrigatórios."}), 400

        # --- SELEÇÃO DE MODELO ---
        if "chirp" in model_nickname:
            final_text_for_api = f"[ESTILO: CHIRP HD] {text_to_narrate}"
            model_fullname = "gemini-2.5-flash-preview-tts" 
            analytics_label = "chirp"
        elif "3.1" in model_nickname:
            final_text_for_api = f"Instrução: {custom_prompt}\n\nTexto: {text_to_narrate}" if custom_prompt else text_to_narrate
            model_fullname = "gemini-3.1-flash-tts-preview"
            analytics_label = model_fullname
        else:
            final_text_for_api = f"[CONTEXTO: {custom_prompt}] {text_to_narrate}" if custom_prompt else text_to_narrate
            model_fullname = "gemini-2.5-pro-preview-tts" if "pro" in model_nickname else "gemini-2.5-flash-preview-tts"
            analytics_label = model_fullname

        logger.info(f"HIVE Subtitles Engine: {origin} -> {analytics_label}")

        # --- CHAMADA REST COM FOCO EM AUDIO + TIMESTAMPS ---
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_fullname}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": final_text_for_api}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voice_name": voice_name
                        }
                    }
                }
            }
        }

        response_audio_bytes = None
        prompt_tokens = 0
        output_tokens = 0
        audio_metadata = "" # Aqui guardaremos os timestamps em Base64

        with httpx.Client(timeout=120.0) as client:
            res = client.post(url, json=payload)
            res_json = res.json()
            
            if res.status_code == 200:
                # 1. Captura Tokens
                usage = res_json.get('usageMetadata', {})
                prompt_tokens = usage.get('promptTokenCount', 0)
                output_tokens = usage.get('candidatesTokenCount', 0)

                # 2. Captura Áudio e Metadados (Timestamps)
                if 'candidates' in res_json and len(res_json['candidates']) > 0:
                    candidate = res_json['candidates'][0]
                    parts = candidate.get('content', {}).get('parts', [])
                    
                    if parts and 'inlineData' in parts[0]:
                        response_audio_bytes = base64.b64decode(parts[0]['inlineData']['data'])
                        
                        # Extrai marcas de tempo se disponíveis (JSON stringificado e codificado em Base64 para o header)
                        # Nota: Em versões Preview, o Gemini retorna audioMetadata com word-level offsets
                        meta_data = candidate.get('audioMetadata', {})
                        if meta_data:
                            audio_metadata = base64.b64encode(json.dumps(meta_data).encode()).decode()

            else:
                return jsonify({"error": f"Google API Error: {res.status_code}"}), res.status_code

        if not response_audio_bytes:
            return jsonify({"error": "Falha na geração."}), 500

        # --- PROCESSAMENTO HI-FI ---
        audio_segment = AudioSegment.from_raw(io.BytesIO(response_audio_bytes), sample_width=2, frame_rate=24000, channels=1)
        audio_segment = effects.normalize(audio_segment, headroom=0.45)
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="128k")
        
        http_response = make_response(send_file(io.BytesIO(mp3_buffer.getvalue()), mimetype='audio/mpeg'))
        
        # HEADERS DE TELEMETRIA E LEGENDAS
        http_response.headers['X-Model-Used'] = analytics_label
        http_response.headers['X-Prompt-Tokens'] = str(prompt_tokens)
        http_response.headers['X-Output-Tokens'] = str(output_tokens)
        if audio_metadata:
            http_response.headers['X-Audio-Metadata'] = audio_metadata
        
        return http_response

    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
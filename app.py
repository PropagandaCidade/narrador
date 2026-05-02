# app.py - VERSÃO 29.0 - WORKER ENGINE (HIVE STABLE) - TOKEN TELEMETRY ENABLED
# LOCAL: Repositório Único (N1, N2, N3, N4, N5) no Railway
# DESCRIÇÃO: Captura usageMetadata (tokens) da API Gemini e repassa via Headers.
# VERSÃO: 29.0 - ADDED X-Prompt-Tokens & X-Output-Tokens HEADERS

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
# Expondo os novos headers para o CORS
CORS(app, expose_headers=['X-Model-Used', 'X-Prompt-Tokens', 'X-Output-Tokens'])

def clean_skill_tags(text):
    if not text: return ""
    cleaned = re.sub(r'</?context_guard>', '', text)
    return cleaned.strip()

@app.route('/')
def home():
    srv = os.environ.get('RAILWAY_SERVICE_NAME', 'Worker')
    return f"Serviço v29.0 ({srv}) - Token Telemetry Online."

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
        if "3.1" in model_nickname:
            if custom_prompt:
                final_text_for_api = f"Instrução de narração: {custom_prompt}\n\nTexto para narrar: {text_to_narrate}"
            else:
                final_text_for_api = text_to_narrate
            model_fullname = "gemini-3.1-flash-tts-preview"
        else:
            final_text_for_api = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {custom_prompt}] {text_to_narrate}" if custom_prompt else text_to_narrate
            model_fullname = "gemini-2.5-pro-preview-tts" if "pro" in model_nickname else "gemini-2.5-flash-preview-tts"

        logger.info(f"HIVE Worker: {origin} -> {model_fullname}")

        # --- CHAMADA REST COM SAFETY MAX OVERRIDE ---
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
        prompt_tokens = 0
        output_tokens = 0
        max_retries = 2

        with httpx.Client(timeout=120.0) as client:
            for attempt in range(max_retries):
                try:
                    res = client.post(url, json=payload)
                    res_json = res.json()
                    
                    if res.status_code == 200:
                        # Extração de Telemetria de Tokens (usageMetadata)
                        usage = res_json.get('usageMetadata', {})
                        prompt_tokens = usage.get('promptTokenCount', 0)
                        output_tokens = usage.get('candidatesTokenCount', 0)

                        if 'candidates' in res_json and len(res_json['candidates']) > 0:
                            candidate = res_json['candidates'][0]
                            
                            if candidate.get('finishReason') in ['SAFETY', 'OTHER']:
                                return jsonify({"error": f"Conteúdo bloqueado pelo filtro do Google ({candidate.get('finishReason')})."}), 400
                                
                            parts = candidate.get('content', {}).get('parts', [])
                            if parts and 'inlineData' in parts[0]:
                                response_audio_bytes = base64.b64decode(parts[0]['inlineData']['data'])
                                break
                        
                        if 'promptFeedback' in res_json and res_json['promptFeedback'].get('blockReason'):
                            reason = res_json['promptFeedback']['blockReason']
                            if attempt == 0 and custom_prompt:
                                payload["contents"][0]["parts"][0]["text"] = text_to_narrate
                                continue
                            return jsonify({"error": f"O Google não permitiu este roteiro (Block: {reason})."}), 400
                            
                    else:
                        error_msg = res_json.get('error', {}).get('message', 'Erro na API')
                        if attempt == max_retries - 1:
                            return jsonify({"error": f"Google API Error: {error_msg}"}), res.status_code
                
                except Exception as e:
                    if attempt == max_retries - 1: raise e
                
                time.sleep(1)

        if not response_audio_bytes:
            return jsonify({"error": "Erro na geração do áudio (Filtros rigorosos)."}), 500

        # --- MOTOR HI-FI ---
        audio_segment = AudioSegment.from_raw(io.BytesIO(response_audio_bytes), sample_width=2, frame_rate=24000, channels=1)
        audio_segment = effects.normalize(audio_segment, headroom=3.0)
        audio_segment = effects.compress_dynamic_range(audio_segment, threshold=-9.0, ratio=3.8, attack=0.5, release=400.0)
        audio_segment = effects.normalize(audio_segment, headroom=0.45)

        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="128k", parameters=["-ar", "44100"])
        
        http_response = make_response(send_file(io.BytesIO(mp3_buffer.getvalue()), mimetype='audio/mpeg'))
        
        # INJEÇÃO DE HEADERS DE TELEMETRIA PARA O DISPATCHER (PHP)
        http_response.headers['X-Model-Used'] = model_fullname
        http_response.headers['X-Prompt-Tokens'] = str(prompt_tokens)
        http_response.headers['X-Output-Tokens'] = str(output_tokens)
        
        return http_response

    except Exception as e:
        logger.error(f"Erro Crítico Worker: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
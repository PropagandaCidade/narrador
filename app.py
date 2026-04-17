# app.py - VERSÃO 28.4 - WORKER ENGINE (HIVE STABLE) - DEFENSIVE REST MODE
# LOCAL: Repositório Único (N1, N2, N3, N4, N5)
# DESCRIÇÃO: Captura de erro real da Google e blindagem contra KeyError 'candidates'.

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
CORS(app, expose_headers=['X-Model-Used'])

def clean_skill_tags(text):
    if not text:
        return ""
    cleaned = re.sub(r'</?context_guard>', '', text)
    return cleaned.strip()

@app.route('/')
def home():
    srv = os.environ.get('RAILWAY_SERVICE_NAME', 'Worker')
    return f"Serviço v28.4 ({srv}) - Hive Defensive REST Online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Requisição inválida."}), 400

        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Chave Gemini não fornecida."}), 500

        text_raw = data.get('text', '')
        text_to_narrate = clean_skill_tags(text_raw)
        voice_name = data.get('voice')
        model_nickname = str(data.get('model_to_use', 'flash')).lower()
        custom_prompt = data.get('custom_prompt', '').strip()
        origin = data.get('origin_interface', 'dashboard')
        
        try:
            temperature = float(data.get('temperature', 0.85))
        except:
            temperature = 0.85

        if not text_to_narrate or not voice_name:
            return jsonify({"error": "Texto e voz são obrigatórios."}), 400

        # Montagem do prompt
        final_text_for_api = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {custom_prompt}] {text_to_narrate}" if custom_prompt else text_to_narrate

        # --- MODEL SHIELD (v28.4) ---
        if "3.1" in model_nickname:
            model_fullname = "gemini-3.1-flash-tts-preview"
        elif "2.5" in model_nickname and "pro" in model_nickname:
            model_fullname = "gemini-2.5-pro-preview-tts"
        elif "2.5" in model_nickname and "flash" in model_nickname:
            model_fullname = "gemini-2.5-flash-preview-tts"
        elif model_nickname in ['pro', 'chirp']:
            model_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_fullname = "gemini-2.5-flash-preview-tts"

        logger.info(f"HIVE Worker: {origin} -> Requisitando {model_fullname} via REST")

        # --- CHAMADA REST DIRETA ---
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_fullname}:generateContent?key={api_key}"
        
        payload = {
            "contents": [
                {"parts": [{"text": final_text_for_api}]}
            ],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice_name}
                    }
                }
            }
        }

        response_audio_bytes = None
        max_retries = 2

        with httpx.Client(timeout=120.0) as client:
            for attempt in range(max_retries):
                try:
                    res = client.post(url, json=payload)
                    res_json = res.json()
                    
                    if res.status_code == 200:
                        # VERIFICAÇÃO DEFENSIVA DA CHAVE 'candidates'
                        if 'candidates' in res_json and len(res_json['candidates']) > 0:
                            content = res_json['candidates'][0].get('content', {})
                            parts = content.get('parts', [])
                            if parts and 'inlineData' in parts[0]:
                                b64_data = parts[0]['inlineData']['data']
                                response_audio_bytes = base64.b64decode(b64_data)
                                break
                            else:
                                # Pode ser que o conteúdo foi bloqueado (Safety Filters)
                                block_reason = res_json['candidates'][0].get('finishReason', 'UNKNOWN')
                                return jsonify({"error": f"Google bloqueou a geração. Motivo: {block_reason}"}), 400
                        else:
                            # Caso não haja 'candidates', logamos o erro real retornado
                            error_msg = res_json.get('error', {}).get('message', 'Estrutura de resposta inválida da Google.')
                            logger.error(f"Resposta inesperada (200): {json.dumps(res_json)}")
                            return jsonify({"error": error_msg}), 400
                    else:
                        error_msg = res_json.get('error', {}).get('message', 'Erro na API Google.')
                        logger.warning(f"Tentativa {attempt+1} falhou: {error_msg}")
                        if attempt == max_retries - 1:
                            return jsonify({"error": f"Google API: {error_msg}"}), res.status_code
                
                except Exception as e:
                    logger.error(f"Erro na conexão REST: {str(e)}")
                    if attempt == max_retries - 1: raise e
                
                time.sleep(1)

        if not response_audio_bytes:
            return jsonify({"error": "Não foi possível extrair áudio da resposta da Google."}), 500

        # --- MOTOR DE PROCESSAMENTO HI-FI ---
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(response_audio_bytes),
            sample_width=2,
            frame_rate=24000,
            channels=1
        )

        audio_segment = effects.normalize(audio_segment, headroom=3.0)
        audio_segment = effects.compress_dynamic_range(
            audio_segment, threshold=-9.0, ratio=3.8, attack=0.5, release=400.0
        )
        audio_segment = effects.normalize(audio_segment, headroom=0.45)

        mp3_buffer = io.BytesIO()
        audio_segment.export(
            mp3_buffer, 
            format="mp3", 
            bitrate="128k", 
            parameters=["-ar", "44100"]
        )
        
        http_response = make_response(send_file(
            io.BytesIO(mp3_buffer.getvalue()),
            mimetype='audio/mpeg'
        ))
        http_response.headers['X-Model-Used'] = model_fullname
        
        return http_response

    except Exception as e:
        logger.error(f"Erro Crítico no Worker: {str(e)}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
# app.py - VERSÃO 28.1 - WORKER ENGINE (HIVE STABLE) - UNARY GENERATION FIX
# LOCAL: Repositório Único (N1, N2, N3, N4, N5)
# DESCRIÇÃO: Mudança para generate_content (Unary) para paridade total com AI Studio.

import os
import io
import logging
import re
import time

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
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
    return f"Serviço v28.1 ({srv}) - Unary Generation Ready."

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

        # Lógica de montagem do Prompt
        if custom_prompt:
            final_text_for_api = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {custom_prompt}] {text_to_narrate}"
        else:
            final_text_for_api = text_to_narrate

        # --- MODEL SHIELD (v28.1) ---
        if "3.1" in model_nickname:
            model_to_use_fullname = "gemini-3.1-flash-tts-preview"
        elif "2.5" in model_nickname and "pro" in model_nickname:
            model_to_use_fullname = "gemini-2.5-pro-preview-tts"
        elif "2.5" in model_nickname and "flash" in model_nickname:
            model_to_use_fullname = "gemini-2.5-flash-preview-tts"
        elif model_nickname in ['pro', 'chirp']:
            model_to_use_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_to_use_fullname = "gemini-2.5-flash-preview-tts"
            
        logger.info(f"HIVE Worker: {origin} -> Requisitando {model_to_use_fullname} (Unary Mode)")

        client = genai.Client(api_key=api_key)

        generate_config = types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["AUDIO"], # Uppercase para paridade total com documentação
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
        )

        # GERAÇÃO UNARY (generate_content) - Resolve o problema de "Stream Empty"
        response_audio_raw = None
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_to_use_fullname, 
                    contents=final_text_for_api, 
                    config=generate_config
                )
                
                # Extração do áudio do candidato
                if (response.candidates and response.candidates[0].content and 
                    response.candidates[0].content.parts and 
                    response.candidates[0].content.parts[0].inline_data):
                    response_audio_raw = response.candidates[0].content.parts[0].inline_data.data
                    break 
                    
            except Exception as e:
                logger.warning(f"Tentativa {attempt+1} falhou para {model_to_use_fullname}: {str(e)}")
                if attempt == max_retries - 1: raise e
                time.sleep(1)

        if not response_audio_raw:
             return jsonify({"error": "Google API não retornou dados de áudio."}), 500

        # --- PROCESSAMENTO ENGINE COMPANDER HI-FI ---
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(response_audio_raw),
            sample_width=2,
            frame_rate=24000,
            channels=1
        )

        audio_segment = effects.normalize(audio_segment, headroom=3.0)
        audio_segment = effects.compress_dynamic_range(
            audio_segment, threshold=-9.0, ratio=3.8, attack=0.5, release=400.0
        )
        audio_segment = effects.normalize(audio_segment, headroom=0.45)

        # EXPORTAÇÃO MP3
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
        http_response.headers['X-Model-Used'] = model_to_use_fullname
        
        return http_response

    except Exception as e:
        logger.error(f"Erro no Worker: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
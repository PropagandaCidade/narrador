# app.py - VERSÃO 27.8 - WORKER ENGINE (HIVE STABLE) - MODEL FLEX SUPPORT
# LOCAL: Repositório Único (N1, N2, N3, N4, N5)
# DESCRIÇÃO: Suporte dinâmico para modelos 2.5 e 3.1 no Prompt Lab.

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
    return f"Serviço v27.8 ({srv}) - Hive Multi-Model Support Online."

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
        model_nickname = data.get('model_to_use', 'flash')
        custom_prompt = data.get('custom_prompt', '').strip()
        origin = data.get('origin_interface', 'dashboard')
        
        try:
            temperature = float(data.get('temperature', 0.85))
        except:
            temperature = 0.85

        if not text_to_narrate or not voice_name:
            return jsonify({"error": "Texto e voz são obrigatórios."}), 400

        # REVERTED PROMPT LOGIC
        if custom_prompt:
            final_text_for_api = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {custom_prompt}] {text_to_narrate}"
        else:
            final_text_for_api = text_to_narrate

        # --- NOVA LÓGICA DE MAPEAMENTO DE MODELO (v27.8) ---
        # 1. Se receber o nome completo do modelo (vindo do Prompt Lab)
        valid_full_models = [
            'gemini-2.5-flash-preview-tts', 
            'gemini-2.5-pro-preview-tts', 
            'gemini-3.1-flash-preview-tts'
        ]
        
        if model_nickname in valid_full_models:
            model_to_use_fullname = model_nickname
        # 2. Se receber apelidos (vindo do Dashboard ou Studio)
        else:
            model_to_use_fullname = "gemini-2.5-pro-preview-tts" if model_nickname in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
            
        logger.info(f"Worker processando: {origin} | Model: {model_to_use_fullname}")

        client = genai.Client(api_key=api_key)

        generate_config = types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
        )

        audio_data_chunks = []
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                audio_data_chunks = [] 
                for chunk in client.models.generate_content_stream(model=model_to_use_fullname, contents=final_text_for_api, config=generate_config):
                    if (chunk.candidates and chunk.candidates[0].content and 
                        chunk.candidates[0].content.parts and 
                        chunk.candidates[0].content.parts[0].inline_data):
                        audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)
                
                if audio_data_chunks:
                    break 
                    
            except Exception as e:
                logger.warning(f"Tentativa {attempt+1} falhou para {model_to_use_fullname}: {str(e)}")
                if attempt == max_retries - 1: 
                    raise e
                time.sleep(0.5)

        if not audio_data_chunks:
             return jsonify({"error": "Google indisponível após tentativas."}), 500

        # --- PROCESSAMENTO ENGINE COMPANDER HI-FI ---
        full_audio_raw = b''.join(audio_data_chunks)
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(full_audio_raw),
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
        http_response.headers['X-Model-Used'] = model_to_use_fullname
        
        return http_response

    except Exception as e:
        logger.error(f"Erro no Worker: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
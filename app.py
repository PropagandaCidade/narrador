# app.py - VERSÃO 25.0 - WORKER ENGINE (HIVE)
# LOCAL: voice-hub/app.py
# DESCRIÇÃO: Separação de Instruções de Sistema do Roteiro (Fix: IA lendo instruções).

import os
import io
import logging
import re

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

from pydub import AudioSegment

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização do Flask App
app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

def clean_skill_tags(text):
    """
    Remove as tags <context_guard> do roteiro.
    """
    if not text:
        return ""
    cleaned = re.sub(r'</?context_guard>', '', text)
    return cleaned.strip()

@app.route('/')
def home():
    server_name = os.environ.get("RAILWAY_SERVICE_NAME", "Worker")
    return f"Voice Hub Worker ({server_name}) v25.0 pronto."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida."}), 400

    # Captura da chave enviada pelo Master Router
    api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        return jsonify({"error": "Chave de API ausente."}), 500

    # 1. Parâmetros de Geração
    text_raw = data.get('text', '')
    text_to_narrate = clean_skill_tags(text_raw)
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')
    
    # Instrução de Sistema (O que a IA deve obedecer mas NÃO falar)
    custom_prompt = data.get('custom_prompt', '').strip()
    
    try:
        temperature = float(data.get('temperature', 0.85))
    except (ValueError, TypeError):
        temperature = 0.85

    if not text_to_narrate or not voice_name:
        return jsonify({"error": "Texto e voz são obrigatórios."}), 400

    try:
        # 2. Configuração do Modelo
        if model_nickname in ['pro', 'chirp']:
            model_to_use_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_to_use_fullname = "gemini-2.5-flash-preview-tts"
            
        logger.info(f"Gerando áudio via {model_to_use_fullname}")
        
        client = genai.Client(api_key=api_key)

        # 3. Geração via Streaming com Separação de Instruções
        audio_data_chunks = []
        
        # Enviamos o custom_prompt como system_instruction para a IA não falar a regra
        for chunk in client.models.generate_content_stream(
            model=model_to_use_fullname,
            contents=text_to_narrate, # Apenas o roteiro aqui
            config=types.GenerateContentConfig(
                system_instruction=custom_prompt if custom_prompt else "Narre com naturalidade.",
                temperature=temperature,
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                )
            )
        ):
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_data_chunks:
             return jsonify({"error": "A IA não gerou áudio. Verifique os parâmetros."}), 500

        # 4. Processamento MP3
        full_audio_raw = b''.join(audio_data_chunks)
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(full_audio_raw),
            sample_width=2,
            frame_rate=24000,
            channels=1
        )
        
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
        
        http_response = make_response(send_file(
            io.BytesIO(mp3_buffer.getvalue()),
            mimetype='audio/mpeg'
        ))
        http_response.headers['X-Model-Used'] = model_nickname
        
        return http_response

    except Exception as e:
        logger.error(f"ERRO NO WORKER: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
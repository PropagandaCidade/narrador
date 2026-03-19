# app.py - VERSÃO 24.0 - WORKER ENGINE (NARRADORES N1-N5)
# LOCAL: voice-hub/app.py (Nos repositórios dos narradores)
# DESCRIÇÃO: Agora aceita API KEY dinâmica vinda do Master Router.

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
    Remove as tags <context_guard> e </context_guard> do roteiro.
    """
    if not text:
        return ""
    cleaned = re.sub(r'</?context_guard>', '', text)
    return cleaned.strip()

@app.route('/')
def home():
    server_name = os.environ.get("RAILWAY_SERVICE_NAME", "Worker Desconhecido")
    return f"Voice Hub Worker ({server_name}) está pronto e aguardando comandos do Master Router."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida (JSON vazio)."}), 400

    # --- NOVIDADE: CAPTURA DA CHAVE DINÂMICA ---
    # Prioriza a chave enviada pelo Master Router. Se não vier, tenta a do ambiente.
    api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        logger.error("ERRO: Nenhuma GEMINI_API_KEY foi fornecida pelo Master Router ou Ambiente.")
        return jsonify({"error": "Chave de API não encontrada para este processamento."}), 500

    # 1. Captura de parâmetros
    text_raw = data.get('text', '')
    text_to_narrate = clean_skill_tags(text_raw)
    
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')
    custom_prompt = data.get('custom_prompt', '').strip()
    
    try:
        temperature = float(data.get('temperature', 0.85))
    except (ValueError, TypeError):
        temperature = 0.85

    if not text_to_narrate or not voice_name:
        return jsonify({"error": "Texto e voz são obrigatórios."}), 400

    try:
        # 2. Preparação do Conteúdo Final
        if custom_prompt:
            final_content = f"[INSTRUÇÃO DE INTERPRETAÇÃO: {custom_prompt}] {text_to_narrate}"
        else:
            final_content = text_to_narrate

        # 3. Mapeamento de Modelos (Gemini 2.5 Preview)
        if model_nickname in ['pro', 'chirp']:
            model_to_use_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_to_use_fullname = "gemini-2.5-flash-preview-tts"
            
        logger.info(f"Processando narração com chave {api_key[:8]}... no modelo {model_to_use_fullname}")
        
        # Inicializa o cliente com a chave recebida
        client = genai.Client(api_key=api_key)

        # 4. Geração via Streaming
        audio_data_chunks = []
        for chunk in client.models.generate_content_stream(
            model=model_to_use_fullname,
            contents=final_content,
            config=types.GenerateContentConfig(
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
             return jsonify({"error": "O Google Gemini não retornou dados de áudio."}), 500

        # 5. Processamento e conversão para MP3
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
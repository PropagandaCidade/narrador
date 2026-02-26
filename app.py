# app.py - VERSÃO 22.1 - DASHBOARD EXPERT MODE (SERVIDOR 01)
# DESCRIÇÃO: Versão corrigida com os modelos Gemini 2.5 Preview.
# Esta versão é o espelho exato do Servidor 02, garantindo consistência total.

import os
import io
import logging

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

@app.route('/')
def home():
    # Identificação para o Servidor 01
    return "Servidor 01 (Dashboard Expert - Gemini 2.5) está online e pronto."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("Recebendo solicitação para /api/generate-audio no Servidor 01")
    
    # 1. Validação da API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("ERRO: GEMINI_API_KEY não encontrada no Servidor 01.")
        return jsonify({"error": "Configuração do servidor incompleta."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida."}), 400

    # 2. Captura de parâmetros
    text_from_php = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')
    
    # Parâmetros Expert do Dashboard
    custom_prompt = data.get('custom_prompt', '').strip()
    try:
        temperature = float(data.get('temperature', 0.85))
    except (ValueError, TypeError):
        temperature = 0.85

    if not text_from_php or not voice_name:
        return jsonify({"error": "Texto e voz são obrigatórios."}), 400

    try:
        # 3. Preparação do Texto com Instruções de Estilo
        if custom_prompt:
            final_content = f"[INSTRUÇÃO DE INTERPRETAÇÃO: {custom_prompt}] {text_from_php}"
            logger.info(f"Aplicando Prompt Expert: {custom_prompt[:100]}...")
        else:
            final_content = text_from_php

        # 4. Mapeamento de Modelos (Utilizando a versão 2.5 Preview conforme solicitado)
        if model_nickname in ['pro', 'chirp']:
            model_to_use_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_to_use_fullname = "gemini-2.5-flash-preview-tts"
            
        logger.info(f"Usando modelo: {model_to_use_fullname} | Temperatura: {temperature}")
        
        client = genai.Client(api_key=api_key)

        # Configuração da Geração
        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        # 5. Geração via Streaming
        audio_data_chunks = []
        for chunk in client.models.generate_content_stream(
            model=model_to_use_fullname,
            contents=final_content,
            config=generate_content_config
        ):
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_data_chunks:
             return jsonify({"error": "API do Google não retornou dados de áudio."}), 500

        # 6. Processamento e conversão para MP3 (Pydub)
        full_audio_data_raw = b''.join(audio_data_chunks)
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(full_audio_data_raw),
            sample_width=2,
            frame_rate=24000,
            channels=1
        )
        
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
        mp3_data = mp3_buffer.getvalue()
        
        # 7. Resposta
        http_response = make_response(send_file(
            io.BytesIO(mp3_data),
            mimetype='audio/mpeg',
            as_attachment=False
        ))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso no Servidor 01: Áudio gerado ({model_nickname}).")
        return http_response

    except Exception as e:
        logger.error(f"ERRO CRÍTICO NO SERVIDOR 01: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
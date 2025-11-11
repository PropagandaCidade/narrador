# app.py - VERSÃO 19.0.1 - CORRIGE OS NOMES DOS MODELOS PARA 2.5 e otimiza para MP3 Mono.

import os
import io
import struct
import logging

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Mantemos as importações originais que funcionam
from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

# Adicionamos pydub para a conversão
from pydub import AudioSegment

# Opcional, mas mantido para consistência com o original
# from text_utils import correct_grammar_for_grams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

@app.route('/')
def home():
    return "Serviço de Narração Unificado v19.0.1 (MP3 Mono) está online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("Recebendo solicitação para /api/generate-audio")
    
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        error_msg = "ERRO CRÍTICO: GEMINI_API_KEY não encontrada no ambiente."
        logger.error(error_msg)
        return jsonify({"error": "Configuração do servidor incompleta."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_process = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')

    if model_nickname == 'chirp':
        model_nickname = 'pro'

    if not text_to_process or not voice_name:
        return jsonify({"error": "Os campos de texto e voz são obrigatórios."}), 400

    try:
        INPUT_CHAR_LIMIT = 4900
        if len(text_to_process) > INPUT_CHAR_LIMIT:
            logger.warning(f"Texto de entrada ({len(text_to_process)} chars) excedeu o limite de {INPUT_CHAR_LIMIT}. O texto será truncado.")
            text_to_process = text_to_process[:INPUT_CHAR_LIMIT]

        # Se você usa o text_utils, descomente a linha abaixo e remova a próxima
        # corrected_text = correct_grammar_for_grams(text_to_process)
        corrected_text = text_to_process

        # --- [INÍCIO DA CORREÇÃO] ---
        # Corrigindo os nomes dos modelos para a versão 2.5, conforme solicitado.
        if model_nickname == 'pro':
            model_to_use_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_to_use_fullname = "gemini-2.5-flash-preview-tts"
        # --- [FIM DA CORREÇÃO] ---
        
        logger.info(f"Usando modelo: {model_to_use_fullname}")
        
        client = genai.Client(api_key=api_key)

        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            max_output_tokens=8192,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        audio_data_chunks = []
        for chunk in client.models.generate_content_stream(
            model=model_to_use_fullname, contents=corrected_text, config=generate_content_config
        ):
            if (chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts and chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data):
                audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_data_chunks:
             return jsonify({"error": "A API respondeu, mas não retornou dados de áudio."}), 500

        full_audio_data_raw = b''.join(audio_data_chunks)
        
        # --- LÓGICA DE CONVERSÃO PARA MP3 MONO ---
        logger.info("Áudio bruto recebido. Convertendo para MP3 Mono...")
        
        # A API retorna áudio PCM (raw) de 1 canal, 24kHz, 16-bit.
        # Precisamos informar esses parâmetros para a pydub.
        # sample_width=2 (16 bits), frame_rate=24000, channels=1
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(full_audio_data_raw),
            sample_width=2,
            frame_rate=24000,
            channels=1
        )
        
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
        mp3_data = mp3_buffer.getvalue()
        
        logger.info(f"Conversão para MP3 concluída. Tamanho: {len(mp3_data) / 1024:.2f} KB")

        http_response = make_response(send_file(
            io.BytesIO(mp3_data), 
            mimetype='audio/mpeg', # Mimetype correto para MP3
            as_attachment=False
        ))
        
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso: Áudio MP3 Mono gerado e enviado ao cliente.")
        return http_response

    except Exception as e:
        error_message = f"Erro inesperado: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
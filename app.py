# app.py - VERSÃO 6.1 - Forçando o deploy com mudança visível.
import os
import io
import struct
import logging

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from text_utils import correct_grammar_for_grams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

def convert_to_wav(audio_data: bytes) -> bytes:
    # Esta função permanece a mesma
    logger.info("Verificando e empacotando dados de áudio para WAV...")
    bits_per_sample = 16
    sample_rate = 24000
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels,
        sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size
    )
    return header + audio_data

@app.route('/')
def home():
    # MUDANÇA VISÍVEL PARA CONFIRMAR O DEPLOY
    return "Serviço de Narração v6.1 - Autenticação Corrigida - Online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("Recebendo solicitação para /api/generate-audio")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        error_msg = "ERRO CRÍTICO: GEMINI_API_KEY não encontrada."
        logger.error(error_msg)
        return jsonify({"error": "Configuração do servidor incompleta."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_process = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')

    if not text_to_process or not voice_name:
        return jsonify({"error": "Os campos de texto e voz são obrigatórios."}), 400

    try:
        logger.info("Aplicando pré-processamento de texto...")
        corrected_text = correct_grammar_for_grams(text_to_process)

        if model_nickname == 'pro':
            model_to_use_fullname = "models/text-to-speech-pro"
        else:
            model_to_use_fullname = "models/text-to-speech"
        
        logger.info(f"Usando modelo: {model_to_use_fullname}")
        
        # A forma correta de autenticar para a biblioteca v0.8.5+
        tts_client = genai.TextToSpeechClient(api_key=api_key)
        
        tts_response = tts_client.text_to_speech(
            model=model_to_use_fullname,
            text=corrected_text,
            voice_name=voice_name
        )

        if not tts_response.audio_content:
            return jsonify({"error": "A API respondeu, mas não retornou dados de áudio."}), 500

        wav_data = tts_response.audio_content
        
        http_response = make_response(send_file(io.BytesIO(wav_data), mimetype='audio/wav', as_attachment=False))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso: Áudio WAV gerado e enviado ao cliente.")
        return http_response

    except (google_exceptions.ResourceExhausted, google_exceptions.PermissionDenied, google_exceptions.Unauthenticated, google_exceptions.ClientError) as e:
        error_message = f"Falha de API que permite nova tentativa: {type(e).__name__} - {e}"
        logger.warning(error_message)
        return jsonify({"error": error_message, "retryable": True}), 429

    except Exception as e:
        error_message = f"Erro inesperado que NÃO permite nova tentativa: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
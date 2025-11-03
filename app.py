# app.py - VERSÃO 5.0 - Utiliza a chamada correta 'text_to_speech' com os modelos TTS corretos.
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

# A função 'convert_to_wav' não é mais necessária, pois a API já retorna WAV.
# Mantida por segurança caso o formato mude.
def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    # Se já for WAV, apenas retorna os dados.
    if 'wav' in mime_type:
        logger.info("Dados de áudio já estão no formato WAV.")
        return audio_data
        
    logger.info(f"Convertendo dados de áudio de {mime_type} para WAV...")
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
    logger.info("Conversão para WAV concluída.")
    return header + audio_data

@app.route('/')
def home():
    return "Serviço de Narração individual está online."

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

        # --- [CORREÇÃO] Usando os nomes de modelo TTS corretos que você forneceu ---
        if model_nickname == 'pro':
            model_to_use_fullname = "models/text-to-speech-pro"
        else:
            model_to_use_fullname = "models/text-to-speech"
        
        logger.info(f"Usando modelo: {model_to_use_fullname}")
        
        # Configura a API key
        genai.configure(api_key=api_key)

        # --- [CORREÇÃO] Usando o método text_to_speech, que é o correto para esta tarefa ---
        tts_response = genai.text_to_speech(
            model=model_to_use_fullname,
            text=corrected_text,
            voice_name=voice_name
        )

        if not tts_response.audio_content:
            return jsonify({"error": "A API respondeu, mas não retornou dados de áudio."}), 500

        # A API retorna WAV, então a conversão é apenas uma salvaguarda.
        wav_data = tts_response.audio_content
        
        http_response = make_response(send_file(io.BytesIO(wav_data), mimetype='audio/wav', as_attachment=False))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso: Áudio WAV gerado e enviado ao cliente.")
        return http_response

    except (google_exceptions.ResourceExhausted, google_exceptions.PermissionDenied, google_exceptions.Unauthenticated, google_exceptions.ClientError) as e:
        error_message = f"Falha de API que permite nova tentativa: {type(e).__name__}"
        logger.warning(error_message)
        return jsonify({"error": error_message, "retryable": True}), 429

    except Exception as e:
        error_message = f"Erro inesperado que NÃO permite nova tentativa: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
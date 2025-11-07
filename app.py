# app.py - VERSÃO 15.2 - Corrige problema de áudio cortado para textos longos.
import os
import io
import mimetypes
import struct
import logging

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

from text_utils import correct_grammar_for_grams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
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
    return "Serviço de Narração Unificado v15.2 está online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("Recebendo solicitação para /api/generate-audio")
    
    # [CORREÇÃO] A chave de API agora é lida do PAYLOAD, não mais do ambiente.
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    api_key = data.get('api_key')
    if not api_key:
        error_msg = "ERRO CRÍTICO: Chave de API não foi fornecida no payload pelo roteador."
        logger.error(error_msg)
        return jsonify({"error": "Configuração de autenticação incompleta."}), 500

    text_to_process = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')

    if not text_to_process or not voice_name:
        return jsonify({"error": "Os campos de texto e voz são obrigatórios."}), 400

    try:
        # --- [INÍCIO DA LÓGICA DE TRUNCAMENTO] ---
        INPUT_CHAR_LIMIT = 3000
        if len(text_to_process) > INPUT_CHAR_LIMIT:
            logger.warning(f"Texto de entrada ({len(text_to_process)} chars) excedeu o limite de {INPUT_CHAR_LIMIT}. O texto será truncado.")
            text_to_process = text_to_process[:INPUT_CHAR_LIMIT]
        # --- [FIM DA LÓGICA DE TRUNCAMENTO] ---

        logger.info("Aplicando pré-processamento de texto para correção de pronúncia...")
        corrected_text = correct_grammar_for_grams(text_to_process)

        if model_nickname == 'pro':
            model_to_use_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_to_use_fullname = "gemini-2.5-flash-preview-tts"
        
        logger.info(f"Usando modelo: {model_to_use_fullname}")
        
        client = genai.Client(api_key=api_key)

        # --- [INÍCIO DA LÓGICA DE AUMENTO DE TOKENS] ---
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            max_output_tokens=8192,  # Permite que a resposta de áudio seja longa
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        # --- [FIM DA LÓGICA DE AUMENTO DE TOKENS] ---
        
        audio_data_chunks = []
        for chunk in client.models.generate_content_stream(
            model=model_to_use_fullname, contents=corrected_text, config=generate_content_config
        ):
            if (chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts and chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data):
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_data_chunks.append(inline_data.data)

        if not audio_data_chunks:
             # Retorna uma mensagem mais clara se a API retornar vazio (pode ser MAX_TOKENS de entrada)
             return jsonify({"error": "A API respondeu, mas não retornou dados de áudio. O texto pode ter excedido o limite de entrada da API."}), 500

        full_audio_data = b''.join(audio_data_chunks)
        wav_data = convert_to_wav(full_audio_data, inline_data.mime_type)
        
        http_response = make_response(send_file(io.BytesIO(wav_data), mimetype='audio/wav', as_attachment=False))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso: Áudio WAV gerado e enviado ao cliente.")
        return http_response

    except google_exceptions.ResourceExhausted as e:
        error_message = f"Cota da API esgotada: {e}"
        logger.warning(error_message)
        return jsonify({"error": error_message, "retryable": True}), 429

    except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated, google_exceptions.ClientError) as e:
        error_message = f"Falha de API que NÃO permite nova tentativa: {type(e).__name__} - {e}"
        logger.warning(error_message)
        return jsonify({"error": error_message, "retryable": False}), 403

    except Exception as e:
        error_message = f"Erro inesperado que NÃO permite nova tentativa: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
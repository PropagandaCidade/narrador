# app.py - VERSÃO FINAL CORRIGIDA SEM ERROS DE SINTAXE
import os
import io
import struct
import logging
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from google import genai
from google.genai import types

# --- Configuração de logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Gera um cabeçalho WAV para os dados de áudio recebidos."""
    logger.info(f"Iniciando conversão de {len(audio_data)} bytes de {mime_type} para WAV...")
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
    """Rota para verificar se o serviço está online."""
    return "Serviço de Narração no Railway está online. (Usando a lógica original de streaming)"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Endpoint principal que gera o áudio."""
    logger.info("="*50)
    logger.info("Nova solicitação recebida para /api/generate-audio")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.critical("ERRO CRÍTICO: GEMINI_API_KEY não encontrada.")
        return jsonify({"error": "Configuração do servidor incompleta: Chave de API ausente."}), 500

    data = request.get_json()
    if not data:
        logger.warning("Requisição inválida: corpo JSON ausente.")
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')

    if not text_to_narrate or not voice_name:
        msg = f"Os campos 'text' e 'voice' são obrigatórios."
        logger.warning(msg)
        return jsonify({"error": msg}), 400
        
    logger.info(f"Texto: '{text_to_narrate[:50]}...' | Voz: '{voice_name}'")

    try:
        # A sua lógica original, que estava correta
        logger.info("Configurando o cliente Google GenAI...")
        client = genai.Client(api_key=api_key)
        
        model_name = "gemini-2.5-pro-preview-tts"
        logger.info(f"Usando o modelo: {model_name}")

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=text_to_narrate)])]
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
        )

        logger.info("Iniciando chamada à API generate_content_stream...")
        audio_data_chunks = []
        
        # Correção do bug original:
        mime_type = "audio/unknown" 
        
        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=generate_content_config
        ):
            if (chunk.candidates and chunk.candidates.content and 
                chunk.candidates.content.parts and
                chunk.candidates.content.parts.inline_data and 
                chunk.candidates.content.parts.inline_data.data):
                
                inline_data = chunk.candidates.content.parts.inline_data
                audio_data_chunks.append(inline_data.data)
                mime_type = inline_data.mime_type

        if not audio_data_chunks:
             error_msg = "A API respondeu, mas não retornou dados de áudio."
             logger.error(error_msg)
             return jsonify({"error": error_msg}), 500

        full_audio_data = b''.join(audio_data_chunks)
        logger.info(f"Dados de áudio completos recebidos ({len(full_audio_data)} bytes). Tipo MIME: {mime_type}")

        wav_data = convert_to_wav(full_audio_data, mime_type)
        
        logger.info("Áudio gerado com sucesso. Enviando resposta...")
        return send_file(
            io.BytesIO(wav_data),
            mimetype='audio/wav',
            as_attachment=False
        )

    except Exception as e:
        error_message = f"Erro ao contatar a API do Google GenAI: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
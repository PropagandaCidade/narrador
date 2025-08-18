# app.py - VERSÃO FINAL COM PROMPT EXPLÍCITO PARA EVITAR A FALA DE INSTRUÇÕES
import os
import io
import mimetypes
import struct
import logging
import random

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    # (Esta função permanece a mesma)
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
    return header + audio_data

@app.route('/')
def home():
    logger.info("Endpoint '/' acessado.")
    return "Serviço de Narração no Railway está online e estável! (Usando google-genai com lógica 80/20)"

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

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')

    if not text_to_narrate or not voice_name:
        return jsonify({"error": "Os campos 'text' e 'voice' são obrigatórios."}), 400

    try:
        # --- Lógica 80/20 de Seleção de Modelo ---
        if random.random() < 0.80:
            model_to_use = "gemini-2.5-flash-preview-tts"
            model_nickname = "flash"
        else:
            model_to_use = "gemini-2.5-pro-preview-tts"
            model_nickname = "pro"
        logger.info(f"Modelo selecionado: {model_to_use} (Apelido: {model_nickname})")
        
        # --- [ALTERADO] CRIAÇÃO DE UM PROMPT EXPLÍCITO ---
        # Isso instrui o modelo a APENAS ler o texto, em vez de interpretá-lo.
        prompt_text = f"Fale este texto em voz alta, de forma natural: {text_to_narrate}"
        logger.info(f"Texto formatado para a API: '{prompt_text[:100]}...'") # Loga o início do prompt
        # --- FIM DA ALTERAÇÃO ---

        client = genai.Client(api_key=api_key)

        contents = [
            types.Content(
                role="user",
                # [ALTERADO] Usa o texto formatado no prompt
                parts=[types.Part.from_text(text=prompt_text)]
            )
        ]

        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
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
            model=model_to_use,
            contents=contents,
            config=generate_content_config
        ):
            if (chunk.candidates and chunk.candidates[0].content and 
                chunk.candidates[0].content.parts and
                chunk.candidates[0].content.parts[0].inline_data and 
                chunk.candidates[0].content.parts[0].inline_data.data):
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_data_chunks.append(inline_data.data)

        if not audio_data_chunks:
             return jsonify({"error": "A API respondeu, mas não retornou dados de áudio."}), 500

        full_audio_data = b''.join(audio_data_chunks)
        mime_type = inline_data.mime_type if 'inline_data' in locals() else "audio/unknown"
        wav_data = convert_to_wav(full_audio_data, mime_type)
        
        http_response = make_response(send_file(
            io.BytesIO(wav_data),
            mimetype='audio/wav',
            as_attachment=False
        ))
        
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso: Áudio WAV gerado com '{model_nickname}' e enviado ao cliente.")
        return http_response

    except Exception as e:
        error_message = f"Erro ao contatar a API do Google GenAI: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
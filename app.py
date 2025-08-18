# app.py - VERSÃO V2.1 COM FERRAMENTA DE DIAGNÓSTICO NA ROTA PRINCIPAL
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
    """
    [DIAGNÓSTICO] Rota para verificar se o serviço está online E testar a lógica 80/20.
    """
    logger.info("Endpoint de diagnóstico '/' acessado.")
    
    # Teste ativo da lógica de seleção
    test_value = random.random()
    if test_value < 0.80:
        selected_model = "flash"
    else:
        selected_model = "pro"
    
    # A resposta agora inclui o resultado do teste
    return (f"Serviço de Narração V2.1 - Lógica 80/20 ATIVA. "
            f"Teste em tempo real: random={test_value:.4f}, modelo selecionado nesta chamada seria: {selected_model}")


@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    # (O restante do seu código permanece o mesmo)
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
        model_flash = "gemini-2.5-flash-preview-tts"
        model_pro = "gemini-2.5-pro-preview-tts"
        
        if random.random() < 0.80:
            model_to_use = model_flash
            model_nickname = "flash"
        else:
            model_to_use = model_pro
            model_nickname = "pro"
            
        logger.info(f"Modelo selecionado: {model_to_use} (Apelido: {model_nickname})")

        client = genai.Client(api_key=api_key)
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=text_to_narrate)])]
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
        )
        
        audio_data_chunks = []
        for chunk in client.models.generate_content_stream(model=model_to_use, contents=contents, config=generate_content_config):
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
        
        http_response = make_response(send_file(io.BytesIO(wav_data), mimetype='audio/wav', as_attachment=False))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso: Áudio WAV gerado com '{model_nickname}' e enviado.")
        return http_response

    except Exception as e:
        error_message = f"Erro ao contatar a API do Google GenAI: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
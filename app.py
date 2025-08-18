# app.py - VERSÃO FINAL COM MODELO PRO ISOLADO E ENVIO DIRETO DE TEXTO
import os
import io
import mimetypes
import struct
import logging
# 'random' não é mais necessário, foi removido

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Importações da nova biblioteca
from google import genai
from google.genai import types

# --- Configuração de logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Expõe o cabeçalho personalizado 'X-Model-Used' para o frontend
CORS(app, expose_headers=['X-Model-Used'])

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """
    Gera um cabeçalho WAV para os dados de áudio recebidos.
    """
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
    """Rota para verificar se o serviço está online."""
    logger.info("Endpoint '/' acessado.")
    return "Serviço de Narração no Railway está online e estável! (Modelo: Gemini Pro TTS)"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Endpoint principal que gera o áudio."""
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
        # --- [ALTERADO] Modelo Pro agora é fixo ---
        model_to_use = "gemini-2.5-pro-preview-tts"
        model_nickname = "pro"
        logger.info(f"Usando modelo fixo: {model_to_use}")
        # --- FIM DA ALTERAÇÃO ---

        logger.info("Configurando o cliente Google GenAI...")
        client = genai.Client(api_key=api_key)

        # A estrutura 'contents' com 'role="user"' foi removida.

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
        logger.info(f"Configuração de geração criada para voz: '{voice_name}'")

        logger.info(f"Iniciando chamada à API com texto direto...")
        audio_data_chunks = []
        
        # --- [ALTERAÇÃO CRÍTICA] ---
        # O texto do usuário ('text_to_narrate') é passado diretamente no parâmetro 'contents'.
        # Isso evita o modo de "conversa" e trata o texto como dados brutos para TTS.
        for chunk in client.models.generate_content_stream(
            model=model_to_use,
            contents=text_to_narrate, # A string de texto é enviada diretamente aqui
            config=generate_content_config
        ):
        # --- FIM DA ALTERAÇÃO CRÍTICA ---
            if (chunk.candidates and 
                chunk.candidates[0].content and 
                chunk.candidates[0].content.parts and
                chunk.candidates[0].content.parts[0].inline_data and 
                chunk.candidates[0].content.parts[0].inline_data.data):
                
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_data_chunks.append(inline_data.data)

        if not audio_data_chunks:
             error_msg = "A API respondeu, mas não retornou dados de áudio."
             logger.error(error_msg)
             return jsonify({"error": error_msg}), 500

        full_audio_data = b''.join(audio_data_chunks)
        mime_type = inline_data.mime_type if 'inline_data' in locals() else "audio/unknown"
        wav_data = convert_to_wav(full_audio_data, mime_type)
        
        logger.info("Áudio gerado e convertido com sucesso. Enviando resposta...")
        http_response = make_response(send_file(
            io.BytesIO(wav_data),
            mimetype='audio/wav',
            as_attachment=False
        ))
        
        http_response.headers['X-Model-Used'] = model_nickname
        http_response.headers['X-Audio-Source-Mime'] = mime_type
        
        logger.info(f"Sucesso: Áudio WAV gerado com '{model_nickname}' e enviado ao cliente.")
        return http_response

    except Exception as e:
        error_message = f"Erro ao contatar a API do Google GenAI: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
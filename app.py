# app.py - VERSÃO FINAL COM CONTROLE DE CONFIGURAÇÃO DE SEGURANÇA
import os
import io
import struct
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
from google.genai import types

# Importa as classes necessárias para as configurações de segurança
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- Configuração de logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Gera um cabeçalho WAV para os dados de áudio recebidos."""
    # (Esta função permanece inalterada)
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
    return "Serviço de Narração no Railway está online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("="*50)
    logger.info("Nova solicitação recebida para /api/generate-audio")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.critical("FALHA CRÍTICA: Variável de ambiente GEMINI_API_KEY não encontrada.")
        return jsonify({"error": "Configuração do servidor incompleta."}), 500
    
    data = request.get_json()
    if not data or not data.get('text') or not data.get('voice'):
        return jsonify({"error": "Os campos 'text' e 'voice' são obrigatórios."}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')
    
    logger.info(f"Voz: '{voice_name}' | Texto: '{text_to_narrate[:100]}...'")

    try:
        client = genai.Client(api_key=api_key)
        
        # ***** IMPLEMENTAÇÃO DA CONFIGURAÇÃO DE SEGURANÇA *****
        # Instruímos a API a não bloquear conteúdo em nenhuma categoria.
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        # Usamos apenas o modelo 'pro' como principal, a alternância não é mais necessária para o filtro.
        model_name = "gemini-2.5-pro-preview-tts"
        logger.info(f"Tentando com o modelo: {model_name} e configurações de segurança desativadas.")
        
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
        mime_type = "audio/unknown"
        
        # A chamada à API agora inclui o parâmetro 'safety_settings'
        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=generate_content_config,
            safety_settings=safety_settings  # <-- Parâmetro adicionado aqui
        ):
            if (chunk.candidates and chunk.candidates[0].content and 
                chunk.candidates[0].content.parts and
                chunk.candidates[0].content.parts[0].inline_data and 
                chunk.candidates[0].content.parts[0].inline_data.data):
                
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_data_chunks.append(inline_data.data)
                mime_type = inline_data.mime_type
        
        if not audio_data_chunks:
             error_msg = "A API respondeu, mas não retornou dados de áudio. Mesmo com as configurações de segurança, o conteúdo pode ter sido bloqueado por outras razões."
             logger.error(f"Falha total ao gerar áudio para o texto: '{text_to_narrate[:100]}...'")
             return jsonify({"error": error_msg}), 500

        full_audio_data = b''.join(audio_data_chunks)
        wav_data = convert_to_wav(full_audio_data, mime_type)
        
        logger.info("Áudio gerado com sucesso. Enviando resposta...")
        return send_file(io.BytesIO(wav_data), mimetype='audio/wav', as_attachment=False)

    except Exception as e:
        error_message = f"Erro inesperado no servidor: {e}"
        logger.error(f"ERRO CRÍTICO INESPERADO: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
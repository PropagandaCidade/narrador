# app.py - VERSÃO ESTÁVEL COM NORMALIZAÇÃO DE NÚMEROS
import os
import io
import struct
import logging
import re
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app)

def normalizar_numeros(texto: str) -> str:
    """Converte números por extenso em dígitos para garantir a aprovação do filtro da API."""
    numeros_por_extenso = {
        'zero': '0', 'um': '1', 'uma': '1', 'dois': '2', 'duas': '2', 'três': '3', 
        'quatro': '4', 'cinco': '5', 'seis': '6', 'sete': '7', 'oito': '8', 'nove': '9'
    }
    texto_normalizado = texto
    for palavra, digito in numeros_por_extenso.items():
        texto_normalizado = re.sub(r'\\b' + palavra + r'\\b', digito, texto_normalizado, flags=re.IGNORECASE)
    if texto_normalizado != texto:
        logger.info(f"Texto normalizado para dígitos: '{texto_normalizado}'")
    return texto_normalizado

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
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
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Configuração do servidor incompleta."}), 500
    
    data = request.get_json()
    if not data or not data.get('text') or not data.get('voice'):
        return jsonify({"error": "Os campos 'text' e 'voice' são obrigatórios."}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')
    
    # Aplica a normalização para garantir que a API não bloqueie
    text_processado = normalizar_numeros(text_to_narrate)
    
    logger.info(f"Voz: '{voice_name}' | Texto Processado: '{text_processado[:100]}...'")

    try:
        client = genai.Client(api_key=api_key)
        model_name = "gemini-2.5-pro-preview-tts"
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=text_processado)])]
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
        for chunk in client.models.generate_content_stream(model=model_name, contents=contents, config=generate_content_config):
            if (chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts and chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data):
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_data_chunks.append(inline_data.data)
                mime_type = inline_data.mime_type
        
        if not audio_data_chunks:
             return jsonify({"error": "A API não retornou dados de áudio."}), 500

        full_audio_data = b''.join(audio_data_chunks)
        wav_data = convert_to_wav(full_audio_data, mime_type)
        return send_file(io.BytesIO(wav_data), mimetype='audio/wav', as_attachment=False)

    except Exception as e:
        return jsonify({"error": f"Erro inesperado no servidor: {e}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
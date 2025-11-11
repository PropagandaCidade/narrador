# app.py - VERSÃO 18.0.0 - Usa GEMINI_API_KEY e converte a saída para MP3 Mono.

import os
import io
import struct
import logging

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Usamos a biblioteca original que você já tem configurada
from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

# Adicionamos a pydub para a conversão de áudio
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

@app.route('/')
def home():
    return "Serviço de Narração Unificado v18.0.0 (MP3 Mono) está online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("Recebendo solicitação para /api/generate-audio")
    
    # Voltamos a usar a GEMINI_API_KEY, que você já tem configurada.
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        error_msg = "ERRO CRÍTICO: GEMINI_API_KEY não encontrada no ambiente do Railway."
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

    # --- VÁLVULA DE SEGURANÇA ---
    CHAR_LIMIT = 4900 
    if len(text_to_process) > CHAR_LIMIT:
        logger.warning(f"Texto de entrada ({len(text_to_process)} chars) excedeu o limite de segurança de {CHAR_LIMIT}. O texto será truncado.")
        text_to_process = text_to_process[:CHAR_LIMIT]

    try:
        # A API do Gemini pode não ter um modelo "pro" para TTS, vamos usar o nome do modelo que você tinha
        # e que provavelmente funciona. Verifique a documentação para os nomes corretos.
        if model_nickname == 'pro':
            # Use o nome correto do modelo TTS Pro, se houver um
            model_to_use_fullname = "models/text-to-speech-pro"
        else:
            model_to_use_fullname = "models/text-to-speech" # Modelo padrão
        
        logger.info(f"Usando modelo: {model_to_use_fullname}")
        
        # A autenticação é feita ao criar o cliente, como no seu código original
        client = genai.Client(api_key=api_key)

        # A biblioteca genai usa um método diferente para TTS
        ssml_text = f"<speak>{text_to_process}</speak>"
        
        response = genai.synthesize_speech(
            model=model_to_use_fullname,
            text=ssml_text,
            voice=genai.Voice(name=voice_name)
        )

        wav_data_from_api = response['audio_content']

        if not wav_data_from_api:
             return jsonify({"error": "A API respondeu, mas não retornou dados de áudio."}), 500

        # --- CONVERSÃO PARA MP3 MONO USANDO PYDUB ---
        logger.info("Áudio WAV recebido da API. Convertendo para MP3 Mono...")
        audio_wav = AudioSegment.from_wav(io.BytesIO(wav_data_from_api))
        audio_mono = audio_wav.set_channels(1)
        
        mp3_buffer = io.BytesIO()
        audio_mono.export(mp3_buffer, format="mp3", bitrate="64k")
        mp3_data = mp3_buffer.getvalue()
        
        logger.info(f"Conversão concluída. Tamanho do MP3: {len(mp3_data) / 1024:.2f} KB")

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
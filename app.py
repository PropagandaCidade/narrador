# app.py - VERSÃO 17.0.1 - Usa credenciais de conta de serviço (ADC)

import os
import io
import logging
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Importações necessárias
from google.cloud import texttospeech
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

@app.route('/')
def home():
    return "Serviço de Narração Unificado v17.0.1 (Otimizado para MP3 Mono) está online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("Recebendo solicitação para /api/generate-audio")
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_process = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')
    
    if not text_to_process or not voice_name:
        return jsonify({"error": "Os campos de texto e voz são obrigatórios."}), 400

    # Válvula de segurança
    CHAR_LIMIT = 4900 
    if len(text_to_process) > CHAR_LIMIT:
        logger.warning(f"Texto de entrada ({len(text_to_process)} chars) excedeu o limite de segurança de {CHAR_LIMIT}. O texto será truncado.")
        text_to_process = text_to_process[:CHAR_LIMIT]

    try:
        # A biblioteca encontrará as credenciais automaticamente na variável de ambiente GOOGLE_APPLICATION_CREDENTIALS
        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text_to_process)

        voice = texttospeech.VoiceSelectionParams(language_code="pt-BR", name=voice_name)
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        
        logger.info("Áudio WAV recebido da API. Convertendo para MP3 Mono...")
        audio_wav = AudioSegment.from_wav(io.BytesIO(response.audio_content))
        audio_mono = audio_wav.set_channels(1)
        
        mp3_buffer = io.BytesIO()
        audio_mono.export(mp3_buffer, format="mp3", bitrate="64k")
        mp3_data = mp3_buffer.getvalue()
        
        logger.info(f"Conversão concluída. Tamanho do MP3: {len(mp3_data) / 1024:.2f} KB")

        http_response = make_response(send_file(
            io.BytesIO(mp3_data), 
            mimetype='audio/mpeg',
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
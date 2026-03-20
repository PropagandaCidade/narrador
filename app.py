# app.py - VERSÃO 26.0 - WORKER ENGINE (HIVE)
# LOCAL: voice-hub/app.py
# DESCRIÇÃO: Tratamento de erros do Google e Limpeza de instruções DNA.
# VERSÃO: 26.0 - ROBUST GOOGLE ERROR CATCHER

import os
import io
import logging
import re
import traceback

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

from pydub import AudioSegment

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

def clean_input_text(text):
    """
    Limpa tags e caracteres que podem confundir o motor TTS.
    """
    if not text:
        return ""
    # Remove tags context_guard e limpa espaços excessivos
    cleaned = re.sub(r'</?context_guard>', '', text)
    cleaned = cleaned.replace('\\"', '"').replace('\\n', '\n')
    return cleaned.strip()

@app.route('/')
def home():
    return f"Worker {os.environ.get('RAILWAY_SERVICE_NAME', 'Narrador')} v26.0 Ativo."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Payload vazio."}), 400

        # Captura de Chave
        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "API KEY ausente no Worker."}), 500

        # Parâmetros
        text_to_narrate = clean_input_text(data.get('text', ''))
        voice_name = data.get('voice')
        model_nickname = data.get('model_to_use', 'flash')
        
        # Limpeza pesada da instrução de sistema para evitar Erro 500 do Google
        custom_prompt = clean_input_text(data.get('custom_prompt', ''))
        
        try:
            temperature = float(data.get('temperature', 0.85))
        except:
            temperature = 0.85

        if not text_to_narrate or not voice_name:
            return jsonify({"error": "Texto e voz são obrigatórios."}), 400

        # Mapeamento de Modelos
        model_fullname = "gemini-2.5-pro-preview-tts" if model_nickname in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
            
        logger.info(f"Iniciando geração: {model_fullname} | Voz: {voice_name}")
        
        client = genai.Client(api_key=api_key)

        # Geração via Streaming
        audio_data_chunks = []
        
        try:
            for chunk in client.models.generate_content_stream(
                model=model_fullname,
                contents=text_to_narrate,
                config=types.GenerateContentConfig(
                    system_instruction=custom_prompt if custom_prompt else "Narre com naturalidade.",
                    temperature=temperature,
                    response_modalities=["audio"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                        )
                    )
                )
            ):
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

            if not audio_data_chunks:
                 logger.error("Google retornou streaming vazio.")
                 return jsonify({"error": "O Google não gerou o áudio. Tente outro locutor ou reduza o texto."}), 500

            # Processamento de Áudio
            full_audio_raw = b''.join(audio_data_chunks)
            audio_segment = AudioSegment.from_raw(
                io.BytesIO(full_audio_raw),
                sample_width=2,
                frame_rate=24000,
                channels=1
            )
            
            mp3_buffer = io.BytesIO()
            audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
            
            response = make_response(send_file(
                io.BytesIO(mp3_buffer.getvalue()),
                mimetype='audio/mpeg'
            ))
            response.headers['X-Model-Used'] = model_nickname
            return response

        except Exception as google_err:
            # Captura o erro específico do Google (como o 500 que vimos no log)
            err_msg = str(google_err)
            logger.error(f"Erro na API do Google: {err_msg}")
            return jsonify({"error": f"Google Gemini Error: {err_msg[:100]}"}), 500

    except Exception as e:
        logger.error(f"Erro Crítico no Worker: {traceback.format_exc()}")
        return jsonify({"error": "Falha interna no processamento do narrador."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
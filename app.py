# app.py - VERSÃO 23.1 - DASHBOARD EXPERT MODE (SERVIDOR 01)
# DESCRIÇÃO: Motor com Retry Automático em caso de falha na API do Google.

import os
import io
import logging
import time
import random

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

from pydub import AudioSegment

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização do Flask App
app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

# Chave de API
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    logger.error("ERRO: GEMINI_API_KEY não encontrada.")

# Modelos
MODEL_TTS_FLASH = "gemini-2.5-flash-preview-tts"
MODEL_TTS_PRO = "gemini-2.5-pro-preview-tts"

@app.route('/')
def home():
    return "Servidor 01 (Dashboard Expert) online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("Requisição para /api/generate-audio")

    data = request.get_json()
    text = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')
    custom_prompt = data.get('custom_prompt', '').strip()

    try:
        temperature = float(data.get('temperature', 0.85))
    except:
        temperature = 0.85

    if not text or not voice_name:
        return jsonify({"error": "Texto ou voz ausentes."}), 400

    # Construção da instrução de sistema
    system_instruction = (
        "Você é um locutor profissional em Português do Brasil. "
        "Leia o texto fielmente, sem interpretações."
    )
    if (custom_prompt):
        system_instruction += f"\nINSTRUÇÕES ADICIONAIS: {custom_prompt}"

    # Seleção do modelo e parâmetros
    model_to_use = MODEL_TTS_PRO if model_nickname in ['pro', 'chirp'] else MODEL_TTS_FLASH
    generate_content_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        )
    )

    # Retry Loop (3 tentativas)
    for attempt in range(3):
        try:
            client = genai.Client(api_key=api_key)
            audio_data_chunks = []

            for chunk in client.models.generate_content_stream(
                model=model_to_use,
                contents=text,
                config=generate_content_config
            ):
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

            if not audio_data_chunks:
                raise Exception("API Google não retornou áudio.")

            # Converter e retornar o áudio
            full_audio_data_raw = b''.join(audio_data_chunks)
            audio_segment = AudioSegment.from_raw(
                io.BytesIO(full_audio_data_raw),
                sample_width=2,
                frame_rate=24000,
                channels=1
            )
            mp3_buffer = io.BytesIO()
            audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
            mp3_data = mp3_buffer.getvalue()

            http_response = make_response(send_file(
                io.BytesIO(mp3_data),
                mimetype='audio/mpeg',
                as_attachment=False
            ))
            http_response.headers['X-Model-Used'] = model_nickname
            
            logger.info(f"Sucesso ({model_nickname}).")
            return http_response

        except Exception as e:
            logger.error(f"Tentativa {attempt + 1} falhou: {e}")
            if attempt < 2:
                time.sleep(random.uniform(1, 3))  # Aguarda antes de tentar novamente
                logger.info(f"Tentando novamente...")
                continue
            else:
                logger.error(f"Todas as tentativas falharam.", exc_info=True)
                return jsonify({"error": f"Serviço de voz indisponível: {e}"}), 500

    return jsonify({"error": "Falha ao gerar áudio após várias tentativas."}), 500
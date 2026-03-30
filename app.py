# app.py - VERSÃO 27.3 - WORKER ENGINE (HIVE STABLE) - FIX: ANTI-CLIPPING & HEADROOM
# LOCAL: Repositório Único (N1, N2, N3, N4, N5)
# DESCRIÇÃO: Processamento de áudio profissional com margem de segurança de -2.0dB para evitar clipping.

import os
import io
import logging
import re

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from pydub import AudioSegment, effects

# 1. CONFIGURAÇÃO DE LOGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HiveWorker")

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

def clean_skill_tags(text):
    if not text:
        return ""
    cleaned = re.sub(r'</?context_guard>', '', text)
    return cleaned.strip()

@app.route('/')
def home():
    srv = os.environ.get('RAILWAY_SERVICE_NAME', 'Worker')
    return f"Serviço v27.3 ({srv}) - Audio Limiter & Normalization Active."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Requisição inválida."}), 400

        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Configuração de chave incompleta."}), 500

        text_raw = data.get('text', '')
        text_to_narrate = clean_skill_tags(text_raw)
        voice_name = data.get('voice')
        model_nickname = data.get('model_to_use', 'flash')
        custom_prompt = data.get('custom_prompt', '').strip()
        
        try:
            temperature = float(data.get('temperature', 0.85))
        except:
            temperature = 0.85

        if not text_to_narrate or not voice_name:
            return jsonify({"error": "Texto e voz são obrigatórios."}), 400

        final_text_for_api = f"[CONTEXTO: {custom_prompt}] {text_to_narrate}" if custom_prompt else text_to_narrate

        model_to_use_fullname = "gemini-2.5-pro-preview-tts" if model_nickname in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
            
        client = genai.Client(api_key=api_key)

        generate_config = types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
        )

        audio_data_chunks = []
        for chunk in client.models.generate_content_stream(model=model_to_use_fullname, contents=final_text_for_api, config=generate_config):
            if (chunk.candidates and chunk.candidates[0].content and 
                chunk.candidates[0].content.parts and 
                chunk.candidates[0].content.parts[0].inline_data):
                audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_data_chunks:
             return jsonify({"error": "Sem dados de áudio do Google."}), 500

        # --- PROCESSAMENTO DE ÁUDIO ANTI-CLIPPING ---
        full_audio_raw = b''.join(audio_data_chunks)
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(full_audio_raw),
            sample_width=2,
            frame_rate=24000,
            channels=1
        )

        # 1. Compressão Dinâmica para dar corpo à voz e uniformidade
        audio_segment = effects.compress_dynamic_range(audio_segment)

        # 2. Normalização com Headroom (Margem de Segurança)
        # Definindo headroom de 2.0 dB, garantimos que o pico máximo fique em -2.0 dBFS.
        # Isso impede que o áudio chegue aos 32.768 "smpl" e cause clipping.
        audio_segment = effects.normalize(audio_segment, headroom=2.0)
        # --------------------------------------------

        mp3_buffer = io.BytesIO()
        # Exportando com bitrate de 64k (pode aumentar para 128k se quiser mais qualidade)
        audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
        
        http_response = make_response(send_file(
            io.BytesIO(mp3_buffer.getvalue()),
            mimetype='audio/mpeg'
        ))
        http_response.headers['X-Model-Used'] = model_nickname
        
        return http_response

    except Exception as e:
        logger.error(f"Erro no Worker: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
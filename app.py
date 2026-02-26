# app.py - VERSÃO 23.1 - STABLE EXPERT (SERVIDOR 01/02)
# LOCAL: app.py
# DESCRIÇÃO: Limpeza de tags e correção de status HTTP para failover do roteador.

import os
import io
import logging
import re

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

def clean_skill_tags(text):
    """Remove tags <context_guard> para não quebrar o motor de voz do Google."""
    if not text: return ""
    return re.sub(r'</?context_guard>', '', text).strip()

@app.route('/')
def home():
    return "Servidor Expert Ativo."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Chave de API ausente no servidor."}), 500

    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Payload vazio."}), 400

        # Texto processado pela Skill (vem com tags que precisamos remover aqui)
        text_to_narrate = clean_skill_tags(data.get('text', ''))
        voice_name = data.get('voice')
        custom_prompt = data.get('custom_prompt', '').strip()
        model_nickname = data.get('model_to_use', 'flash')
        
        try:
            temp = float(data.get('temperature', 0.85))
        except:
            temp = 0.85

        if not text_to_narrate or not voice_name:
            return jsonify({"error": "Texto ou Voz ausentes."}), 400

        # Mapeamento estrito de modelos para a SDK GenAI
        # Nota: 'gemini-2.0-flash' é o mais estável para TTS no momento
        model_id = "gemini-2.0-flash"
        if model_nickname in ['pro', 'chirp']:
            model_id = "gemini-2.0-pro-exp-02-05"

        client = genai.Client(api_key=api_key)

        # Instrução de estilo + Roteiro limpo
        if custom_prompt:
            final_content = f"ESTILO: {custom_prompt}\n\nTEXTO: {text_to_narrate}"
        else:
            final_content = text_to_narrate

        # Geração
        audio_chunks = []
        for chunk in client.models.generate_content_stream(
            model=model_id,
            contents=final_content,
            config=types.GenerateContentConfig(
                temperature=temp,
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                )
            )
        ):
            if chunk.candidates and chunk.candidates[0].content.parts:
                audio_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_chunks:
            return jsonify({"error": "O Google não gerou áudio."}), 500

        # Conversão MP3
        full_raw = b''.join(audio_chunks)
        audio_segment = AudioSegment.from_raw(io.BytesIO(full_raw), sample_width=2, frame_rate=24000, channels=1)
        
        mp3_buf = io.BytesIO()
        audio_segment.export(mp3_buf, format="mp3", bitrate="64k")
        
        resp = make_response(send_file(io.BytesIO(mp3_buf.getvalue()), mimetype='audio/mpeg'))
        resp.headers['X-Model-Used'] = model_id
        return resp

    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        # GARANTE QUE O RETORNO SEJA 500 PARA O ROTEADOR PULAR PARA O PRÓXIMO
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
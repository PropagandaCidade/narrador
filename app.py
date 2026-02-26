# app.py - VERSÃO 23.2 - FINAL STABLE (DASHBOARD EXPERT)
# LOCAL: Servidor 01 e 02 (Railway)
# DESCRIÇÃO: IDs de modelos corrigidos e limpeza de tags de Skill.

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
    """Remove as tags <context_guard> para o Google não tentar lê-las."""
    if not text: return ""
    return re.sub(r'</?context_guard>', '', text).strip()

@app.route('/')
def home():
    return "Servidor Expert Online (v23.2)"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Chave de API ausente no Servidor."}), 500

    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Payload vazio."}), 400

        # 1. Limpa o texto vindo do PHP com Skills
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

        # 2. Mapeamento de Modelos Estáveis
        # 'gemini-2.0-flash' é o ID correto para a geração de áudio atual.
        # 'gemini-1.5-flash' é o fallback mais seguro se o 2.0 falhar.
        if model_nickname in ['pro', 'chirp']:
            model_id = "gemini-1.5-pro" 
        else:
            model_id = "gemini-2.0-flash"

        client = genai.Client(api_key=api_key)

        # 3. Instrução Expert + Texto Limpo
        if custom_prompt:
            final_content = f"Estilo: {custom_prompt}\n\nTexto: {text_to_narrate}"
        else:
            final_content = text_to_narrate

        logger.info(f"Gerando no Servidor 01 | Modelo: {model_id} | Voz: {voice_name}")

        # 4. Geração do Áudio
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
            return jsonify({"error": "Falha na resposta do Google (Audio Vazio)."}), 500

        # 5. Processamento e Exportação
        full_raw = b''.join(audio_chunks)
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(full_raw), 
            sample_width=2, 
            frame_rate=24000, 
            channels=1
        )
        
        mp3_buf = io.BytesIO()
        audio_segment.export(mp3_buf, format="mp3", bitrate="64k")
        
        resp = make_response(send_file(io.BytesIO(mp3_buf.getvalue()), mimetype='audio/mpeg'))
        resp.headers['X-Model-Used'] = model_id
        return resp

    except Exception as e:
        logger.error(f"Erro Crítico: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
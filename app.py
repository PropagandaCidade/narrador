# app.py - VERSÃO 22.2 - OPTIMIZED FOR SKILLS & STABILITY
# LOCAL: Servidores 01 e 02 (Dashboard Expert)

import os
import io
import logging
import re

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types

from pydub import AudioSegment

# Configuração de logging detalhada
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

def clean_context_tags(text):
    """
    Remove as tags <context_guard> mas mantém o conteúdo.
    Isso evita que a IA tente interpretar as tags XML como parte do roteiro.
    """
    if not text:
        return ""
    cleaned = re.sub(r'</?context_guard>', '', text)
    return cleaned.strip()

@app.route('/')
def home():
    return "Servidor Expert (Gemini 2.0/2.5) Ativo."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Configuração: GEMINI_API_KEY ausente."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Payload vazio."}), 400

    text_raw = data.get('text', '')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')
    custom_prompt = data.get('custom_prompt', '').strip()
    
    try:
        temp = float(data.get('temperature', 0.85))
    except:
        temp = 0.85

    # 1. Limpeza da Skill (mantendo a fonética aplicada pelo PHP)
    text_to_process = clean_context_tags(text_raw)

    if not text_to_process or not voice_name:
        return jsonify({"error": "Texto ou Voz não fornecidos."}), 400

    try:
        # 2. Construção do Prompt (Priorizando a Skill aplicada no texto)
        # Injetamos o custom_prompt como uma instrução de sistema/contexto
        if custom_prompt:
            final_content = f"INSTRUÇÃO DE ESTILO: {custom_prompt}\n\nROTEIRO: {text_to_process}"
        else:
            final_content = text_to_process

        # 3. Mapeamento de Modelos (Garantindo Fallback para 2.0 se 2.5 falhar)
        # Nota: IDs Preview mudam com frequência na API do Google
        model_name = "gemini-2.0-flash" 
        if model_nickname in ['pro', 'chirp']:
            model_name = "gemini-2.0-pro-exp-02-05" # Ou seu ID 2.5 específico

        logger.info(f"Gerando áudio: Modelo {model_name} | Voz {voice_name}")

        client = genai.Client(api_key=api_key)

        config = types.GenerateContentConfig(
            temperature=temp,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
        )

        audio_chunks = []
        # Gerando conteúdo
        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=final_content,
            config=config
        ):
            if chunk.candidates and chunk.candidates[0].content.parts:
                audio_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_chunks:
            raise Exception("Google GenAI não retornou dados de áudio.")

        # 4. Processamento de Áudio com Pydub
        raw_data = b''.join(audio_chunks)
        
        try:
            audio_seg = AudioSegment.from_raw(
                io.BytesIO(raw_data),
                sample_width=2,
                frame_rate=24000,
                channels=1
            )
            
            mp3_buf = io.BytesIO()
            # O 'bitrate' e 'format' exigem ffmpeg instalado no Railway!
            audio_seg.export(mp3_buf, format="mp3", bitrate="64k")
            mp3_data = mp3_buf.getvalue()
        except Exception as pydub_err:
            logger.error(f"Erro Pydub (Provável falta de FFmpeg): {pydub_err}")
            # Fallback: Se falhar a conversão MP3, tentamos enviar o RAW (wav) ou erro
            return jsonify({"error": "Erro na codificação MP3. Verifique o FFmpeg no servidor."}), 500

        response = make_response(send_file(
            io.BytesIO(mp3_data),
            mimetype='audio/mpeg'
        ))
        response.headers['X-Model-Used'] = model_name
        return response

    except Exception as e:
        logger.error(f"Erro no Processamento: {str(e)}")
        return jsonify({"error": f"Erro na geração: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
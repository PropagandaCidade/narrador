# app.py - VERSÃO 27.1 - WORKER ENGINE (HIVE STABLE)
# LOCAL: Repositório Único (N1, N2, N3, N4, N5)
# DESCRIÇÃO: Baseado na versão 21.1 estável com suporte a chaves dinâmicas.
# VERSÃO: 27.1 - REVERTED PROMPT LOGIC FOR STABILITY

import os
import io
import logging
import re

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from pydub import AudioSegment

# 1. CONFIGURAÇÃO DE LOGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HiveWorker")

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

def clean_skill_tags(text):
    """
    Remove as tags <context_guard> do roteiro, mantendo a compatibilidade.
    """
    if not text:
        return ""
    cleaned = re.sub(r'</?context_guard>', '', text)
    return cleaned.strip()

@app.route('/')
def home():
    srv = os.environ.get('RAILWAY_SERVICE_NAME', 'Worker')
    return f"Serviço de Narração Hive v27.1 ({srv}) está online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Requisição inválida (JSON vazio)."}), 400

        # CAPTURA DE CHAVE DINÂMICA (Enviada pelo Master Router)
        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            logger.error("ERRO: Nenhuma API KEY fornecida.")
            return jsonify({"error": "Configuração de chave incompleta no cluster."}), 500

        # 2. CAPTURA DE PARÂMETROS (Lógica v21.1)
        text_raw = data.get('text', '')
        text_to_narrate = clean_skill_tags(text_raw)
        
        voice_name = data.get('voice')
        model_nickname = data.get('model_to_use', 'flash')
        custom_prompt = data.get('custom_prompt', '').strip()
        
        try:
            # Mantemos a temperatura flexível se enviada, ou 0.85 como padrão
            temperature = float(data.get('temperature', 0.85))
        except:
            temperature = 0.85

        if not text_to_narrate or not voice_name:
            return jsonify({"error": "Texto e voz são obrigatórios."}), 400

        # 3. MONTAGEM DO TEXTO FINAL (Exata lógica da v21.1)
        if custom_prompt:
            final_text_for_api = f"[CONTEXTO/ESTILO DE NARRAÇÃO: {custom_prompt}] {text_to_narrate}"
            logger.info(f"Aplicando Prompt v21.1: {custom_prompt[:50]}...")
        else:
            final_text_for_api = text_to_narrate

        # 4. MAPEAMENTO DE MODELOS
        if model_nickname in ['pro', 'chirp']:
            model_to_use_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_to_use_fullname = "gemini-2.5-flash-preview-tts"
            
        client = genai.Client(api_key=api_key)

        # 5. CONFIGURAÇÃO DE GERAÇÃO (Estrutura estável original)
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
        
        # Inicia o streaming do Google
        for chunk in client.models.generate_content_stream(
            model=model_to_use_fullname,
            contents=final_text_for_api,
            config=generate_config
        ):
            if (chunk.candidates and chunk.candidates[0].content and 
                chunk.candidates[0].content.parts and 
                chunk.candidates[0].content.parts[0].inline_data):
                
                audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_data_chunks:
             return jsonify({"error": "O Google não retornou dados de áudio para este roteiro."}), 500

        # 6. PROCESSAMENTO MP3 (Pydub)
        full_audio_raw = b''.join(audio_data_chunks)
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(full_audio_raw),
            sample_width=2,
            frame_rate=24000,
            channels=1
        )
        
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
        
        http_response = make_response(send_file(
            io.BytesIO(mp3_buffer.getvalue()),
            mimetype='audio/mpeg'
        ))
        
        # Headers de rastreio para o Dashboard/Admin
        http_response.headers['X-Model-Used'] = model_nickname
        
        return http_response

    except Exception as e:
        logger.error(f"Erro no Worker: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
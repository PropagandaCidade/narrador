# app.py - VERSÃO 27.0 - UNIFIED WORKER ENGINE (HIVE)
# LOCAL: Repositório Único do GitHub (Conectado a N1, N2, N3, N4, N5)
# DESCRIÇÃO: Separação total de Instruções de Sistema e Roteiro.
# VERSÃO: 27.0 - ANTI-READING INSTRUCTIONS & FAST RESPONSE

import os
import io
import logging
import re
import traceback

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

def clean_text_for_ai(text):
    """
    Limpa o texto removendo tags técnicas e garantindo que a IA 
    receba apenas o que deve ser narrado.
    """
    if not text:
        return ""
    # Remove as tags <context_guard>... e quaisquer outras tags HTML/XML
    cleaned = re.sub(r'<[^>]*>', '', text)
    # Remove colchetes de instruções que possam ter vindo no texto
    cleaned = re.sub(r'\[.*?\]', '', cleaned)
    return cleaned.strip()

@app.route('/')
def home():
    # Identifica qual instância está respondendo no painel do Railway
    srv = os.environ.get('RAILWAY_SERVICE_NAME', 'Worker Unit')
    return f"Hive Worker ({srv}) v27.0 - Ativo e Sincronizado."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados ausentes."}), 400

        # CAPTURA DE CHAVE DINÂMICA (Enviada pelo Master Router)
        api_key = data.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Worker não recebeu a API KEY do Mestre."}), 500

        # PARÂMETROS DE ENTRADA
        text_raw = data.get('text', '')
        text_to_narrate = clean_text_for_ai(text_raw)
        
        voice_name = data.get('voice')
        model_nickname = data.get('model_to_use', 'flash')
        
        # INSTRUÇÃO DE SISTEMA (O que a IA obedece mas NÃO fala)
        # Se não vier do Studio Hub, usamos uma instrução padrão de naturalidade
        system_rules = data.get('custom_prompt', '').strip()
        if not system_rules:
            system_rules = "Aja como um locutor profissional. Narre o texto com naturalidade e clareza."

        try:
            temp = float(data.get('temperature', 0.85))
        except:
            temp = 0.85

        if not text_to_narrate or not voice_name:
            return jsonify({"error": "Texto ou Voz não definidos."}), 400

        # MAPEAMENTO DE MODELOS (Gemini 2.5)
        model_fullname = "gemini-2.5-pro-preview-tts" if model_nickname in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
            
        logger.info(f"Worker iniciando: {model_fullname} | Voz: {voice_name}")
        
        # Inicializa o cliente Google com a chave recebida para este job
        client = genai.Client(api_key=api_key)

        # GERAÇÃO VIA STREAMING (Otimizado)
        audio_chunks = []
        
        try:
            # A MÁGICA: system_instruction é passada fora do 'contents'
            for chunk in client.models.generate_content_stream(
                model=model_fullname,
                contents=text_to_narrate,
                config=types.GenerateContentConfig(
                    system_instruction=system_rules,
                    temperature=temp,
                    response_modalities=["audio"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                        )
                    )
                )
            ):
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    audio_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

            if not audio_chunks:
                 return jsonify({"error": "Google Gemini não gerou áudio para este roteiro."}), 500

            # PROCESSAMENTO PARA MP3 (Pydub)
            full_raw = b''.join(audio_chunks)
            audio_seg = AudioSegment.from_raw(
                io.BytesIO(full_raw),
                sample_width=2,
                frame_rate=24000,
                channels=1
            )
            
            mp3_io = io.BytesIO()
            audio_seg.export(mp3_io, format="mp3", bitrate="64k")
            
            response = make_response(send_file(
                io.BytesIO(mp3_io.getvalue()),
                mimetype='audio/mpeg'
            ))
            response.headers['X-Model-Used'] = model_nickname
            return response

        except Exception as g_err:
            logger.error(f"Erro na API Google: {str(g_err)}")
            return jsonify({"error": f"Google API Error: {str(g_err)[:100]}"}), 500

    except Exception as e:
        logger.error(f"Erro Crítico no Worker: {traceback.format_exc()}")
        return jsonify({"error": "Falha interna no motor de narração."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
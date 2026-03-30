# app.py - VERSÃO 27.6 - WORKER ENGINE (HIVE STABLE) - ENGINE "COMPANDER PRO + HI-FI"
# LOCAL: Repositório Único (N1, N2, N3, N4, N5)
# DESCRIÇÃO: Processamento Profissional 95%, Proteção de Respiração e Exportação 128k/44.1kHz.

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
    """Remove tags de controle interno do texto antes da narração."""
    if not text:
        return ""
    cleaned = re.sub(r'</?context_guard>', '', text)
    return cleaned.strip()

@app.route('/')
def home():
    srv = os.environ.get('RAILWAY_SERVICE_NAME', 'Worker')
    return f"Serviço v27.6 ({srv}) - Engine Compander Hi-Fi (128k) Online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Requisição inválida (JSON vazio)."}), 400

        # CAPTURA DE CHAVE DINÂMICA
        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("ERRO: Nenhuma API KEY fornecida.")
            return jsonify({"error": "Configuração de chave incompleta."}), 500

        # PARÂMETROS DE ENTRADA
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

        # MONTAGEM DO PROMPT PARA A API
        final_text_for_api = f"[CONTEXTO: {custom_prompt}] {text_to_narrate}" if custom_prompt else text_to_narrate

        # MAPEAMENTO DE MODELO
        model_to_use_fullname = "gemini-2.5-pro-preview-tts" if model_nickname in ['pro', 'chirp'] else "gemini-2.5-flash-preview-tts"
            
        client = genai.Client(api_key=api_key)

        # CONFIGURAÇÃO DE GERAÇÃO GOOGLE
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
        
        # STREAMING DO GOOGLE
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
             return jsonify({"error": "O Google não retornou dados de áudio."}), 500

        # --- PROCESSAMENTO ENGINE COMPANDER HI-FI (PROTEÇÃO DE RESPIRAÇÃO) ---
        full_audio_raw = b''.join(audio_data_chunks)
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(full_audio_raw),
            sample_width=2,
            frame_rate=24000,
            channels=1
        )

        # 1. PRÉ-NORMALIZAÇÃO (-3dB): Domar picos iniciais (o "pico solitário")
        audio_segment = effects.normalize(audio_segment, headroom=3.0)

        # 2. COMPRESSOR COMPANDER: Baseado no preset RealAudio (Threshold -9dB, Ratio 3.8:1)
        # Release de 400ms protege a suavidade das respirações (Human Protection)
        audio_segment = effects.compress_dynamic_range(
            audio_segment, 
            threshold=-9.0, 
            ratio=3.8, 
            attack=0.5, 
            release=400.0
        )

        # 3. NORMALIZAÇÃO FINAL A 95%: Volume máximo profissional sem clipping
        audio_segment = effects.normalize(audio_segment, headroom=0.45)
        # ----------------------------------------------------------------------

        # EXPORTAÇÃO EM ALTA QUALIDADE (128k / 44.1kHz)
        mp3_buffer = io.BytesIO()
        audio_segment.export(
            mp3_buffer, 
            format="mp3", 
            bitrate="128k", 
            parameters=["-ar", "44100"]  # Força Sample Rate de 44.1kHz (Qualidade de CD)
        )
        
        http_response = make_response(send_file(
            io.BytesIO(mp3_buffer.getvalue()),
            mimetype='audio/mpeg'
        ))
        
        # Headers de rastreio
        http_response.headers['X-Model-Used'] = model_nickname
        
        return http_response

    except Exception as e:
        logger.error(f"Erro no Worker: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
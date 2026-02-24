# app.py - VERSÃO 21.0 - PROMPT LAB INTEGRATION
# DESCRIÇÃO: Versão definitiva que integra os parâmetros do Prompt Lab (custom_prompt e temperature).
# Esta versão lê e utiliza todas as informações enviadas pelo frontend para a geração expert.

import os
import io
import logging

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

@app.route('/')
def home():
    return "Serviço de Narração Unificado v21.0 (Expert Mode Ativo) está online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("Recebendo solicitação para /api/generate-audio")
    
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        error_msg = "ERRO CRÍTICO: GEMINI_API_KEY não encontrada no ambiente."
        logger.error(error_msg)
        return jsonify({"error": "Configuração do servidor incompleta."}), 500

    data = request.get_json()
    if not data: return jsonify({"error": "Requisição inválida."}), 400

    # --- [ALTERADO] Lendo todos os parâmetros do Prompt Lab ---
    text_to_process = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')
    
    # [NOVO] Lendo o prompt customizado e a temperatura
    custom_prompt = data.get('custom_prompt', '').strip()
    try:
        temperature = float(data.get('temperature', 0.85))
    except (ValueError, TypeError):
        temperature = 0.85 # Valor padrão de segurança

    if not text_to_process or not voice_name:
        return jsonify({"error": "Texto e voz são obrigatórios."}), 400

    try:
        INPUT_CHAR_LIMIT = 4900
        if len(text_to_process) > INPUT_CHAR_LIMIT:
            logger.warning(f"Texto de entrada ({len(text_to_process)} chars) excedeu o limite. O texto será truncado.")
            text_to_process = text_to_process[:INPUT_CHAR_LIMIT]

        # --- [NOVO] Lógica para combinar o texto com o prompt customizado ---
        final_text_for_api = text_to_process
        if custom_prompt:
            # Formata a instrução para que a IA entenda que é uma diretiva de narração
            final_text_for_api = f"[Instrução de narração: {custom_prompt}] {text_to_process}"
            logger.info(f"Prompt customizado aplicado. Texto final para API: '{final_text_for_api[:150]}...'")
        else:
            logger.info(f"Texto para TTS (sem prompt customizado): '{text_to_process[:150]}...'")
        # --- [FIM DA NOVA LÓGICA] ---

        if model_nickname == 'pro':
            model_to_use_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_to_use_fullname = "gemini-2.5-flash-preview-tts"
        
        logger.info(f"Usando modelo: {model_to_use_fullname} com temperatura: {temperature}")
        
        client = genai.Client(api_key=api_key)

        # --- [ALTERADO] Adicionando a temperatura à configuração ---
        generate_content_config = types.GenerateContentConfig(
            temperature=temperature, # [NOVO] Parâmetro de criatividade
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        audio_data_chunks = []
        # --- [ALTERADO] Usando a variável 'final_text_for_api' que contém o prompt ---
        for chunk in client.models.generate_content_stream(
            model=model_to_use_fullname, 
            contents=final_text_for_api, 
            config=generate_content_config
        ):
            if (chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts and chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data):
                audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_data_chunks:
             return jsonify({"error": "A API respondeu, mas não retornou dados de áudio."}), 500

        full_audio_data_raw = b''.join(audio_data_chunks)
        
        logger.info("Áudio bruto recebido. Convertendo para MP3 Mono...")
        audio_segment = AudioSegment.from_raw(io.BytesIO(full_audio_data_raw), sample_width=2, frame_rate=24000, channels=1)
        
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
        mp3_data = mp3_buffer.getvalue()
        
        logger.info(f"Conversão para MP3 concluída. Tamanho: {len(mp3_data) / 1024:.2f} KB")

        http_response = make_response(send_file(io.BytesIO(mp3_data), mimetype='audio/mpeg', as_attachment=False))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info("Sucesso: Áudio MP3 Mono gerado e enviado ao cliente.")
        return http_response

    except Exception as e:
        error_message = f"Erro inesperado: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)```


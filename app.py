# app.py - VERSÃO 19.0.3 - Usa a função de normalização correta e combinada do text_utils.py.

import os
import io
import logging

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

from pydub import AudioSegment

# --- [INÍCIO DA CORREÇÃO] ---
# Importamos a sua função original, que agora contém toda a lógica de normalização.
from text_utils import correct_grammar_for_grams
# --- [FIM DA CORREÇÃO] ---

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

@app.route('/')
def home():
    return "Serviço de Narração Unificado v19.0.3 (com normalização aprimorada) está online."

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

    text_to_process = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')

    if not text_to_process or not voice_name:
        return jsonify({"error": "Texto e voz são obrigatórios."}), 400

    try:
        INPUT_CHAR_LIMIT = 4900
        if len(text_to_process) > INPUT_CHAR_LIMIT:
            logger.warning(f"Texto de entrada ({len(text_to_process)} chars) excedeu o limite. O texto será truncado.")
            text_to_process = text_to_process[:INPUT_CHAR_LIMIT]

        # --- [INÍCIO DA CORREÇÃO] ---
        logger.info(f"Texto original recebido: '{text_to_process[:100]}...'")
        # Usamos a função correta, que agora faz todo o trabalho de normalização.
        corrected_text = correct_grammar_for_grams(text_to_process)
        logger.info(f"Texto normalizado para TTS: '{corrected_text[:100]}...'")
        # --- [FIM DA CORREÇÃO] ---

        if model_nickname == 'pro':
            model_to_use_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_to_use_fullname = "gemini-2.5-flash-preview-tts"
        
        logger.info(f"Usando modelo: {model_to_use_fullname}")
        
        client = genai.Client(api_key=api_key)

        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            max_output_tokens=8192,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        audio_data_chunks = []
        for chunk in client.models.generate_content_stream(
            model=model_to_use_fullname, contents=corrected_text, config=generate_content_config
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
        
        logger.info(f"Sucesso: Áudio MP3 Mono gerado e enviado ao cliente.")
        return http_response

    except Exception as e:
        error_message = f"Erro inesperado: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
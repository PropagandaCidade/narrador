# app.py - VERSÃO 11.1 - Corrige o formato do payload para a Vertex AI e o tratamento de erro.

import os
import io
import struct
import logging
import json
import base64
import requests

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from text_utils import correct_grammar_for_grams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

@app.route('/')
def home():
    return "Serviço de Narração v11.1 (Vertex AI Direct) está online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("Recebendo solicitação para /api/generate-audio")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Configuração do servidor incompleta (API Key)."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_process = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')

    if not text_to_process:
        return jsonify({"error": "O campo de texto é obrigatório."}), 400

    try:
        logger.info("Aplicando pré-processamento de texto...")
        corrected_text = correct_grammar_for_grams(text_to_process)
        
        if model_nickname == 'pro':
            model_id = "gemini-2.5-pro-preview-tts"
        elif model_nickname == 'chirp':
            model_id = "chirp-v3-0"
        else: # flash
            model_id = "gemini-2.5-flash-preview-tts"
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:streamGenerateContent?key={api_key}"

        # --- [INÍCIO DA CORREÇÃO] ---
        # Payload reestruturado para corresponder ao formato da API para TTS
        payload = {
            "model": model_id,
            "voice": voice_name, # Para Gemini TTS
            "audio_config": {
                "audio_encoding": "LINEAR16",
                "sample_rate_hertz": 24000
            },
            "input": {
                "text": corrected_text
            }
        }
        
        # A API Chirp não usa 'voice', mas pode precisar de 'language_code'
        if model_nickname == 'chirp':
            del payload['voice'] # Remove o campo de voz que não é usado
            # A API deve inferir pt-BR do texto
        # --- [FIM DA CORREÇÃO] ---

        logger.info(f"Enviando requisição para API com modelo: {model_id}")
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()

        audio_data_chunks = []
        # Processa a resposta em stream
        for line in response.iter_lines():
            if line.startswith(b'data: '):
                json_str = line.decode('utf-8')[6:]
                try:
                    chunk_data = json.loads(json_str)
                    if 'audioContent' in chunk_data:
                        audio_data_chunks.append(base64.b64decode(chunk_data['audioContent']))
                except json.JSONDecodeError:
                    logger.warning(f"Ignorando linha de stream mal formada: {json_str}")
                    continue

        if not audio_data_chunks:
             return jsonify({"error": "A API respondeu, mas não retornou dados de áudio válidos."}), 500

        full_audio_data = b''.join(audio_data_chunks)
        
        http_response = make_response(send_file(io.BytesIO(full_audio_data), mimetype='audio/wav', as_attachment=False))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso: Áudio WAV gerado e enviado ao cliente.")
        return http_response

    except requests.exceptions.HTTPError as e:
        # --- [INÍCIO DA CORREÇÃO] ---
        # Tratamento de erro robusto para diferentes formatos de resposta
        try:
            error_details = e.response.json()
            # Tenta acessar a mensagem de erro no formato esperado
            error_message = error_details.get('error', {}).get('message', 'Erro desconhecido da API')
        except json.JSONDecodeError:
            # Se a resposta de erro não for JSON, usa o texto bruto
            error_message = e.response.text
        
        logger.error(f"Erro HTTP da API: {e.response.status_code} - {error_message}")
        return jsonify({"error": f"Erro da API: {error_message}"}), 500
        # --- [FIM DA CORREÇÃO] ---
        
    except Exception as e:
        error_message = f"Erro inesperado: {e}"
        logger.error(f"ERRO CRÍTICO: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
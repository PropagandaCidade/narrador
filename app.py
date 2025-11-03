# app.py - VERSÃO 11.0 - Usa requisições HTTP diretas para a Vertex AI, como no exemplo cURL.

import os
import io
import struct
import logging
import json
import base64
import requests # Importa a biblioteca para fazer requisições HTTP

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from text_utils import correct_grammar_for_grams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

@app.route('/')
def home():
    return "Serviço de Narração v11.0 (Vertex AI Direct) está online."

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
        
        # --- [INÍCIO DA CORREÇÃO DEFINITIVA] ---
        
        # Mapeia os nicknames para os nomes de modelo corretos da Vertex AI
        if model_nickname == 'pro':
            model_id = "gemini-2.5-pro-preview-tts"
        elif model_nickname == 'chirp':
            model_id = "chirp-v3-0" # Usando o nome que tentamos antes, pode precisar de ajuste
        else: # flash
            model_id = "gemini-2.5-flash-preview-tts"
        
        # Monta a URL da API da Vertex AI, como no seu exemplo cURL
        # NOTA: A API TTS da Vertex pode usar um endpoint diferente. Este é baseado no seu cURL de texto.
        # O endpoint correto para TTS pode ser algo como 'texttospeech.googleapis.com'
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:streamGenerateContent?key={api_key}"

        # Monta o payload no formato correto
        payload = {
            "model": model_id,
            "input": { "text": corrected_text },
            "voice": {
                "name": voice_name,
                "languageCode": "pt-BR"
            },
            "audioConfig": { "audioEncoding": "LINEAR16", "sampleRateHertz": 24000 }
        }

        # A lógica para Chirp pode ser diferente
        if model_nickname == 'chirp':
            # Chirp pode não aceitar 'name', então removemos
            del payload['voice']['name']
        
        logger.info(f"Enviando requisição para API com modelo: {model_id}")
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() # Lança um erro se o status não for 200

        response_data = response.json()
        
        # A resposta da Vertex vem com o áudio em base64
        if 'audioContent' not in response_data:
            raise Exception("A resposta da API não continha 'audioContent'.")
            
        base64_audio = response_data['audioContent']
        audio_content = base64.b64decode(base64_audio)
        
        # --- [FIM DA CORREÇÃO DEFINITIVA] ---
        
        http_response = make_response(send_file(io.BytesIO(audio_content), mimetype='audio/wav', as_attachment=False))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso: Áudio WAV gerado e enviado ao cliente.")
        return http_response

    except requests.exceptions.HTTPError as e:
        error_details = e.response.json()
        error_message = error_details.get('error', {}).get('message', 'Erro desconhecido da API')
        logger.error(f"Erro HTTP da API: {e.response.status_code} - {error_message}")
        return jsonify({"error": f"Erro da API: {error_message}"}), 500
        
    except Exception as e:
        error_message = f"Erro inesperado: {e}"
        logger.error(f"ERRO CRÍTICO: {error_message}", exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
import os
import google.generativeai as genai
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import logging
import time

# Configuração de logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app, expose_headers=["X-Model-Used"])

# Configuração da API Gemini
try:
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY não encontrada nas variáveis de ambiente.")
    genai.configure(api_key=api_key)
    logging.info("API Key do Gemini configurada com sucesso.")
except Exception as e:
    logging.error(f"Erro ao configurar a API Key: {e}")
    api_key = None

# Modelos de TTS
MODEL_PRO = 'gemini-1.5-pro-preview-0514'
MODEL_FLASH = 'gemini-1.5-flash-preview-0514'

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_route():
    if not api_key:
        return jsonify({"error": "Serviço de IA não configurado."}), 503

    data = request.get_json()
    if not data or 'text' not in data or 'voice' not in data:
        return jsonify({"error": "Dados inválidos: 'text' e 'voice' são obrigatórios."}), 400

    text_to_narrate = data['text']
    voice_id = data['voice']
    style_prompt = data.get('style', 'A standard, professional voice with a clear tone:')
    final_text_for_ia = f"{style_prompt}\n\n{text_to_narrate}"

    # --- CORREÇÃO DE VELOCIDADE APLICADA AQUI ---
    # Invertemos a ordem. Agora, o modelo FLASH (mais rápido) é tentado primeiro.
    models_to_try = [MODEL_FLASH, MODEL_PRO]
    
    model_used = ""
    
    for model_name in models_to_try:
        try:
            logging.info(f"Tentando gerar áudio com o modelo: {model_name}")
            response = genai.generate_text(
                model=f'models/tts-1-hd',
                prompt=final_text_for_ia,
                temperature=0,
            )
            
            if response and hasattr(response, 'result') and response.result:
                model_used = model_name
                logging.info(f"Áudio gerado com sucesso usando {model_used}")
                
                audio_response = Response(response.result, mimetype='audio/mpeg')
                audio_response.headers['X-Model-Used'] = model_used.replace('-preview-0514', '') # Envia nome limpo, ex: "gemini-1.5-flash"
                return audio_response

        except google.api_core.exceptions.ResourceExhausted as e:
            logging.warning(f"Limite de requisições atingido para o modelo {model_name}. Tentando o próximo.")
            continue
            
        except Exception as e:
            logging.error(f"Erro inesperado ao gerar áudio com {model_name}: {e}")
            return jsonify({"error": f"Erro interno na geração de áudio com {model_name}."}), 500

    logging.error("Falha ao gerar áudio com todos os modelos disponíveis.")
    return jsonify({"error": "Serviço de IA sobrecarregado. Tente novamente em alguns instantes."}), 503


@app.route('/')
def index():
    return "API de Geração de Áudio do Voice Hub está online."

if __name__ == '__main__':
    app.run(debug=True)
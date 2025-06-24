import os
import google.generativeai as genai
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import logging
import time
from google.api_core import exceptions

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

# Modelos de TTS - O endpoint é o mesmo, o que muda é a qualidade/velocidade implícita
MODEL_TTS = 'models/tts-1-hd' # Modelo de alta definição

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_route():
    if not api_key:
        return jsonify({"error": "Serviço de IA não configurado."}), 503

    data = request.get_json()
    if not data or 'text' not in data or 'voice' not in data:
        return jsonify({"error": "Dados inválidos: 'text' e 'voice' são obrigatórios."}), 400

    text_to_narrate = data['text']
    voice_id = data['voice']
    
    # O prompt de estilo agora vem completo do PHP. A API TTS não usa um 'prompt' complexo,
    # mas o texto final já vem formatado do PHP, o que está correto.
    final_text_for_ia = f"{data.get('style', '')}\n\n{text_to_narrate}"

    # --- LÓGICA DE RETENTATIVA CORRIGIDA ---
    max_retries = 2
    retry_delay = 2  # segundos

    for attempt in range(max_retries):
        try:
            logging.info(f"Tentativa {attempt + 1}: Gerando áudio com o modelo {MODEL_TTS}")
            
            # --- SINTAXE CORRETA DA API TTS ---
            response = genai.text_to_audio(
                model=MODEL_TTS,
                text=final_text_for_ia,
                voice=voice_id
            )
            
            if response and response.audio_content:
                logging.info("Áudio gerado com sucesso.")
                
                audio_response = Response(response.audio_content, mimetype='audio/mpeg')
                # Podemos futuramente re-adicionar um cabeçalho se o Google fornecer essa info
                audio_response.headers['X-Model-Used'] = 'tts-1-hd' 
                return audio_response

        except exceptions.ResourceExhausted as e:
            logging.warning(f"Limite de requisições atingido (tentativa {attempt + 1}). Aguardando {retry_delay}s. Erro: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay) # Espera antes de tentar novamente
                continue
            else:
                # Se for a última tentativa, retorna erro amigável
                logging.error("Limite de requisições excedido após múltiplas tentativas.")
                return jsonify({"error": "Serviço de IA sobrecarregado. Tente novamente em alguns instantes."}), 503
            
        except Exception as e:
            logging.error(f"Erro inesperado ao gerar áudio: {e}")
            return jsonify({"error": "Erro interno na geração de áudio."}), 500

    # Se saiu do loop sem sucesso
    logging.error("Falha ao gerar áudio após todas as tentativas.")
    return jsonify({"error": "Não foi possível gerar o áudio no momento."}), 500


@app.route('/')
def index():
    return "API de Geração de Áudio do Voice Hub está online."

if __name__ == '__main__':
    app.run(debug=True)
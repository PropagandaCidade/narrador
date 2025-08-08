# app.py - VERSÃO FINAL E DEFINITIVA (COM LOGGING APERFEIÇOADO)
import os
import io
import logging
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
# Importação correta e única necessária
import google.generativeai as genai

# --- Configuração de logging para facilitar o debug ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Configuração de CORS que já sabemos que funciona
CORS(app) 

@app.route('/')
def home():
    """Rota para verificar se o serviço está online."""
    logger.info("Endpoint '/' acessado.")
    return "Serviço de Narração no Railway está online e estável!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Endpoint principal que gera o áudio."""
    logger.info("Recebendo solicitação para /api/generate-audio")
    
    # 1. Obter a chave da API do ambiente do Railway
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        error_msg = "ERRO CRÍTICO: GEMINI_API_KEY não encontrada nas variáveis de ambiente."
        logger.error(error_msg)
        return jsonify({"error": "Configuração do servidor incompleta: Chave de API ausente."}), 500

    # 2. Obter e validar os dados da requisição
    data = request.get_json()
    if not data:
        error_msg = "Requisição inválida, corpo JSON ausente."
        logger.warning(error_msg)
        return jsonify({"error": error_msg}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')

    if not text_to_narrate or not voice_name:
        error_msg = "Os campos 'text' e 'voice' são obrigatórios."
        logger.warning(f"{error_msg} Recebido: text={bool(text_to_narrate)}, voice={bool(voice_name)}")
        return jsonify({"error": error_msg}), 400

    try:
        # 3. Configurar a API
        logger.info("Configurando a API do Google Generative AI...")
        genai.configure(api_key=api_key)
        
        logger.info(f"Gerando áudio para: '{text_to_narrate[:50]}...' com voz: '{voice_name}' usando o modelo 'gemini-2.5-pro-preview-tts'")
        
        # --- A CORREÇÃO FINAL ESTÁ AQUI ---
        # Usamos a função simples 'text_to_speech' e especificamos
        # o modelo exato. O 'voice' é passado diretamente para a função.
        response = genai.text_to_speech(
            text=text_to_narrate,
            voice=voice_name, # Parâmetro correto para especificar a voz
            model='gemini-2.5-pro-preview-tts' # Modelo TTS de pré-visualização
        )
        # --- FIM DA CORREÇÃO ---
        
        # 4. Extrair e verificar os dados de áudio
        wav_data = response.audio_content
        if not wav_data:
            error_msg = "Não foi possível gerar o áudio. A resposta da API veio vazia."
            logger.error(error_msg)
            return jsonify({"error": error_msg}), 500

        # 5. Preparar e enviar a resposta de sucesso
        logger.info("Áudio gerado com sucesso. Enviando resposta...")
        http_response = make_response(send_file(
            io.BytesIO(wav_data),
            mimetype='audio/wav',
            as_attachment=False
        ))
        # Adicionando cabeçalho personalizado para identificar o modelo usado
        http_response.headers['X-Model-Used'] = "gemini-2.5-pro-preview-tts"
        logger.info("Sucesso: Áudio gerado e enviado ao cliente.")
        return http_response

    except Exception as e:
        # Captura qualquer erro que ocorra na comunicação com a API do Google
        error_message = f"Erro ao contatar a API do Google Gemini: {e}"
        logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True) # exc_info=True para log detalhado
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Iniciando aplicação Flask na porta {port}")
    app.run(host='0.0.0.0', port=port)

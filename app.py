# app.py - VERSÃO FINAL E DEFINITIVA
import os
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Importação correta e única necessária para o Gemini
import google.generativeai as genai

app = Flask(__name__)

# Configuração de CORS aberta que já sabemos que funciona
CORS(app) 

@app.route('/')
def home():
    """Rota para verificar se o serviço está online."""
    return "Serviço de Narração no Railway está online e estável!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Endpoint principal que gera o áudio usando o método de alto nível."""
    
    # 1. Obter a chave da API das variáveis de ambiente do Railway
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERRO CRÍTICO: A variável de ambiente GEMINI_API_KEY não foi encontrada no servidor.")
        return jsonify({"error": "Configuração do servidor incompleta: Chave de API ausente."}), 500

    # 2. Obter e validar os dados da requisição JSON enviada pelo frontend
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')

    if not text_to_narrate or not voice_name:
        return jsonify({"error": "Os campos 'text' e 'voice' são obrigatórios."}), 400

    try:
        # 3. USANDO O MÉTODO MAIS SIMPLES E MODERNO
        genai.configure(api_key=api_key)
        
        print(f"Gerando áudio para: '{text_to_narrate[:50]}...' com voz: '{voice_name}'")

        # 4. A função 'text_to_speech' é a forma mais direta e recomendada
        response = genai.text_to_speech(
            text=text_to_narrate,
            voice=voice_name,
            model='models/text-to-speech' # Modelo padrão de alta qualidade
        )
        
        # 5. Verifica se a resposta contém o áudio
        if not response.audio_content:
            return jsonify({"error": "Não foi possível gerar o áudio. A resposta da API veio vazia."}), 500
        
        # 6. Prepara o áudio para ser enviado como resposta
        wav_data = response.audio_content
        
        http_response = make_response(send_file(
            io.BytesIO(wav_data),
            mimetype='audio/wav',
            as_attachment=False
        ))
        http_response.headers['X-Model-Used'] = "Pro"
        
        print("Sucesso: Áudio gerado e enviado ao cliente.")
        return http_response

    except Exception as e:
        # Captura qualquer erro que ocorra na comunicação com a API do Google
        error_message = f"Erro ao contatar a API do Google Gemini: {e}"
        print(f"ERRO CRÍTICO NA API: {error_message}")
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    # Esta parte permite que a aplicação rode usando a porta que o Railway designa
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
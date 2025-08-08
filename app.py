# app.py - VERSÃO FINAL E DEFINITIVA
import os
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Importação correta e única necessária
import google.generativeai as genai

app = Flask(__name__)

# Configuração de CORS que já sabemos que funciona
CORS(app) 

@app.route('/')
def home():
    """Rota para verificar se o serviço está online."""
    return "Serviço de Narração no Railway está online e estável!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Endpoint principal que gera o áudio."""
    
    # 1. Obter a chave da API do ambiente do Railway
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERRO CRÍTICO: GEMINI_API_KEY não encontrada.")
        return jsonify({"error": "Configuração do servidor incompleta: Chave de API ausente."}), 500

    # 2. Obter e validar os dados da requisição
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')

    if not text_to_narrate or not voice_name:
        return jsonify({"error": "Os campos 'text' e 'voice' são obrigatórios."}), 400

    try:
        # 3. Configurar a API
        genai.configure(api_key=api_key)
        
        print(f"Gerando áudio para: '{text_to_narrate[:50]}...' com voz: '{voice_name}'")

        # --- A CORREÇÃO FINAL ESTÁ AQUI ---
        # Usamos a função simples 'text_to_speech' e especificamos
        # o modelo exato que você sugeriu, garantindo compatibilidade.
        response = genai.text_to_speech(
            text=text_to_narrate,
            voice=voice_name,
            model='gemini-2.5-pro-preview-tts' # <-- SUA SUGESTÃO APLICADA AQUI
        )
        # --- FIM DA CORREÇÃO ---
        
        # 4. Extrair e verificar os dados de áudio
        wav_data = response.audio_content
        
        if not wav_data:
            return jsonify({"error": "Não foi possível gerar o áudio. A resposta da API veio vazia."}), 500
        
        # 5. Preparar e enviar a resposta de sucesso
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
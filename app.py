# app.py - Versão FINAL E COMPLETA
import os
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# --- IMPORTAÇÃO CORRETA ---
# Importa o pacote da biblioteca e o apelida de 'genai'
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURAÇÃO DE CORS ABERTA ---
# Permite requisições de QUALQUER origem para QUALQUER rota.
# Isso garante que o erro de CORS não acontecerá.
CORS(app)

@app.route('/')
def home():
    """Rota para verificar se o serviço está online."""
    return "Serviço de Narração no Railway está online!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Endpoint principal que recebe texto e retorna um áudio WAV."""
    
    # 1. Obter a chave da API das variáveis de ambiente
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERRO CRÍTICO: A variável de ambiente GEMINI_API_KEY não foi encontrada no servidor.")
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
        # 3. Configurar a biblioteca com a chave (forma moderna)
        genai.configure(api_key=api_key)

        print(f"Gerando áudio para o texto: '{text_to_narrate[:70]}...' com a voz: '{voice_name}'")

        # 4. Chamar a API de Texto-para-Fala (forma simples e moderna)
        response = genai.text_to_speech(
            text=text_to_narrate,
            voice=voice_name,
            model='models/text-to-speech-standard'
        )

        # 5. Verificar e enviar a resposta
        if not response.audio_content:
            print("ERRO: A API do Gemini não retornou conteúdo de áudio para o texto fornecido.")
            return jsonify({"error": "Não foi possível gerar o áudio. O texto pode ser inválido ou a API está indisponível."}), 500

        # Os dados já vêm em formato WAV, prontos para serem enviados
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
        # Captura e loga qualquer erro da API para facilitar a depuração futura
        error_message = f"Erro ao contatar a API do Google Gemini: {e}"
        print(f"ERRO CRÍTICO NA API: {error_message}")
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    # Configuração para rodar localmente para testes, usando a porta que o Railway fornecer
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
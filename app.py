# app.py - Versão FINAL, COM CORS CORRIGIDO
import os
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# --- IMPORTAÇÃO CORRETA ---
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURAÇÃO DE CORS FINAL E CORRIGIDA ---
# Permite requisições de múltiplas origens, incluindo com e sem 'www'
# O '*' permite que qualquer header (como Content-Type) seja enviado.
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Se você quiser ser mais restrito (RECOMENDADO APÓS FUNCIONAR):
# origins = ["https://propagandacidadeaudio.com.br", "https://www.propagandacidadeaudio.com.br"]
# CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=True)
# --- FIM DA CONFIGURAÇÃO DE CORS ---

@app.route('/')
def home():
    """Rota para verificar se o serviço está online."""
    return "Serviço de Narração no Railway está online e com CORS corrigido!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Endpoint principal que recebe texto e retorna um áudio WAV."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERRO: A variável de ambiente GEMINI_API_KEY não foi encontrada.")
        return jsonify({"error": "Chave de API do servidor não configurada."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')

    if not text_to_narrate or not voice_name:
        return jsonify({"error": "Os campos 'text' e 'voice' são obrigatórios."}), 400

    try:
        genai.configure(api_key=api_key)
        print(f"Gerando áudio para o texto: '{text_to_narrate[:50]}...' com a voz: '{voice_name}'")

        response = genai.text_to_speech(
            text=text_to_narrate,
            voice=voice_name,
            model='models/text-to-speech-standard'
        )

        if not response.audio_content:
            print("ERRO: A API do Gemini não retornou conteúdo de áudio.")
            return jsonify({"error": "Não foi possível gerar o áudio."}), 500

        wav_data = response.audio_content
        
        http_response = make_response(send_file(
            io.BytesIO(wav_data),
            mimetype='audio/wav',
            as_attachment=False
        ))
        http_response.headers['X-Model-Used'] = "Pro"
        print("Áudio gerado e enviado com sucesso.")
        return http_response

    except Exception as e:
        error_message = f"Erro ao contatar a API do Google Gemini: {e}"
        print(f"Ocorreu um erro na API: {error_message}")
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
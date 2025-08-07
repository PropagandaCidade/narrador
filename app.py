# app.py - Versão FINAL com a chamada de API CORRIGIDA
import os
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)

CORS(app) 

@app.route('/')
def home():
    return "Serviço de Narração no Railway está online!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
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
        
        print(f"Gerando áudio para o texto: '{text_to_narrate[:70]}...' com a voz: '{voice_name}'")

        # --- CORREÇÃO ESTÁ AQUI ---
        # A função correta é 'generate_content' com os parâmetros específicos de TTS.
        model = genai.GenerativeModel(model_name='models/text-to-speech')
        
        response = model.generate_content(
            text_to_narrate,
            voice=voice_name
        )
        # --- FIM DA CORREÇÃO ---

        if not response.audio_content:
            return jsonify({"error": "Não foi possível gerar o áudio. O texto pode ser inválido ou a API está indisponível."}), 500

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
        error_message = f"Erro ao contatar a API do Google Gemini: {e}"
        print(f"ERRO CRÍTICO NA API: {error_message}")
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
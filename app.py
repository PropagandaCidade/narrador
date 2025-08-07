# app.py - VERSÃO FINAL E CORRIGIDA
import os
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Importações corretas para a API do Gemini
import google.generativeai as genai
from google.generativeai import types

app = Flask(__name__)

# Configuração de CORS que já está funcionando
CORS(app) 

@app.route('/')
def home():
    """Rota para verificar se o serviço está online."""
    return "Serviço de Narração no Railway está online e estável!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Endpoint principal que gera o áudio usando o método de baixo nível oficial."""
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
        
        tts_model = genai.GenerativeModel(model_name='models/text-to-speech')

        print(f"Gerando áudio para: '{text_to_narrate[:50]}...' com voz: '{voice_name}'")

        # --- A CORREÇÃO FINAL ESTÁ AQUI ---
        # A API espera uma string "audio", não uma constante.
        generation_config = types.GenerateContentConfig(
            response_modalities=["audio"], # <-- ESTA É A LINHA CORRIGIDA
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        response = tts_model.generate_content(
            contents=[text_to_narrate],
            config=generation_config
        )
        
        audio_part = response.candidates[0].content.parts[0]
        wav_data = audio_part.inline_data.data
        
        if not wav_data:
            return jsonify({"error": "Não foi possível gerar o áudio."}), 500
        
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
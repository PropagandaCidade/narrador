# app.py - Versão FINAL com a ESTRUTURA da API CORRIGIDA
import os
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Importa os módulos corretos
import google.generativeai as genai
from google.generativeai import types

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

        # --- A CORREÇÃO FINAL ESTÁ AQUI ---
        # 1. O modelo correto para TTS.
        tts_model = genai.GenerativeModel(model_name='models/text-to-speech')

        # 2. O conteúdo deve ser uma lista de partes.
        contents = [text_to_narrate]

        # 3. A configuração correta que envolve SpeechConfig e VoiceConfig.
        generation_config = types.GenerateContentConfig(
            response_modalities=[types.GenerateContentResponse.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        # 4. A chamada correta para a API
        response = tts_model.generate_content(
            contents=contents,
            config=generation_config
        )
        # --- FIM DA CORREÇÃO FINAL ---
        
        # 5. Acessando o áudio da resposta
        audio_part = response.candidates[0].content.parts[0]
        wav_data = audio_part.inline_data.data
        
        if not wav_data:
            return jsonify({"error": "Não foi possível gerar o áudio. A resposta da API estava vazia."}), 500
        
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
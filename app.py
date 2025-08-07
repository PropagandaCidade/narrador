# app.py - Versão FINAL com os PARÂMETROS da API CORRIGIDOS
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

        # --- CORREÇÃO FINAL ESTÁ AQUI ---
        # A forma correta de passar os parâmetros de voz e modelo
        # é através do objeto 'generation_config'.
        tts_model = genai.GenerativeModel(model_name='gemini-1.5-flash') # Usamos um modelo base
        
        response = tts_model.generate_content(
            text_to_narrate,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                response_mime_type="audio/wav",
                tts_model="text-to-speech-standard",
                tts_voice=voice_name
            )
        )
        # --- FIM DA CORREÇÃO FINAL ---
        
        # A resposta de áudio agora está no primeiro candidato
        if not (response.candidates and response.candidates[0].content.parts):
             return jsonify({"error": "Não foi possível gerar o áudio. A resposta da API estava vazia."}), 500

        audio_part = response.candidates[0].content.parts[0]
        wav_data = audio_part.inline_data.data
        
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
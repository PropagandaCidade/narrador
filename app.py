import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, Content

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/generate": {"origins": "*"}})  # Permite requisições do frontend (substitua "*" pelo domínio da Hostinger em produção)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise SystemExit("ERRO CRÍTICO: GEMINI_API_KEY não encontrada.")
genai.configure(api_key=GEMINI_API_KEY)

@app.route('/generate', methods=['POST'])
def generate_audio_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição JSON inválida"}), 400

    text = data.get('text')
    style = data.get('style')
    voice = data.get('voice')

    if not all([text, style, voice]):
        return jsonify({"error": "Dados incompletos"}), 400

    try:
        model = genai.GenerativeModel("gemini-2.5-pro-preview-tts")
        generation_config = GenerationConfig(
            response_mime_type="audio/wav",
            speech_config={
                "voice_config": {
                    "prebuilt_voice_config": {"voice_name": voice}
                }
            }
        )
        response = model.generate_content(
            [Content(parts=[{"text": f"{style} {text}"})],
            generation_config=generation_config
        )

        if not response.candidates[0].content.parts[0].inline_data.data:
            raise ValueError("A API não retornou dados de áudio na resposta.")

        audio_data = response.candidates[0].content.parts[0].inline_data.data
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        return jsonify({
            "success": True,
            "model_used": "Pro",
            "audio_data": audio_base64
        })

    except Exception as e:
        error_message = f"Falha na comunicação com a API do Google: {str(e)}"
        print(f"ERRO: {error_message}")
        return jsonify({"error": error_message}), 502

@app.route('/')
def home():
    return "Serviço de Geração de Áudio - Online"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
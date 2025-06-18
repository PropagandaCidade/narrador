import os
import base64
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)

# --- Configuração da Chave da API do Google ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise SystemExit("ERRO CRÍTICO: Variável de ambiente GEMINI_API_KEY não foi encontrada no Render.")

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
        # A chamada mais simples e direta possível para um modelo de TTS
        model_name = 'models/gemini-2.5-pro-preview-tts'
        print(f"INFO: Gerando áudio com o modelo: {model_name}")
        
        model = genai.GenerativeModel(model_name)
        
        # O prompt é o que a API espera
        prompt = f"{style} {text}"
        
        # A resposta de áudio é o resultado direto
        response = model.generate_content(prompt, stream=False)
        
        audio_part = response.candidates[0].content.parts[0]
        audio_data = audio_part.inline_data.data
        
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        return jsonify({
            "success": True,
            "model_used": "Pro", # Simplificado por enquanto
            "audio_data": audio_base64
        })

    except Exception as e:
        print(f"ERRO: Falha na comunicação com a API do Google: {e}")
        return jsonify({"error": f"Falha na comunicação com a API do Google: {e}"}), 502

@app.route('/')
def home():
    return "Serviço de Geração de Áudio (Versão Simplificada) - Online"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
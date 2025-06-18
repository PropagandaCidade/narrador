import os
import base64
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise SystemExit("ERRO CRÍTICO: GEMINI_API_KEY não encontrada.")
genai.configure(api_key=GEMINI_API_KEY)

@app.route('/generate', methods=['POST'])
def generate_audio_endpoint():
    data = request.get_json()
    if not data: return jsonify({"error": "Requisição JSON inválida"}), 400

    text = data.get('text')
    style = data.get('style')
    voice = data.get('voice')

    if not all([text, style, voice]):
        return jsonify({"error": "Dados incompletos"}), 400

    try:
        # --- A CHAMADA CORRETA E MODERNA PARA TTS ---
        model_name = "gemini-2.5-pro-preview-tts" # Usando apenas o Pro, como sugerido
        print(f"INFO: Gerando áudio com o modelo: {model_name} e a voz: {voice}")
        
        # O prompt é uma string única combinando estilo e texto.
        full_prompt = f"{style} {text}"
        
        # A nova API usa uma chamada de função direta
        audio_data = genai.generate_speech(
            model=f'models/{model_name}',
            prompt=full_prompt,
            voice=voice,
        )

        if not audio_data.audio_data:
             raise ValueError("A API não retornou dados de áudio na resposta.")

        audio_base64 = base64.b64encode(audio_data.audio_data).decode('utf-8')

        return jsonify({
            "success": True,
            "model_used": "Pro",
            "audio_data": audio_base64
        })

    except Exception as e:
        error_message = f"Falha na comunicação com a API do Google: {e}"
        print(f"ERRO: {error_message}")
        return jsonify({"error": error_message}), 502

@app.route('/')
def home():
    return "Serviço de Geração de Áudio (Versão Simplificada e Corrigida) - Online"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
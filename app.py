import os
import base64
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise SystemExit("ERRO CRÍTICO: Variável de ambiente GEMINI_API_KEY não encontrada.")

genai.configure(api_key=GEMINI_API_KEY)

def generate_audio_from_model(model_name, style_prompt, text_to_narrate, voice_name):
    print(f"INFO: Tentando gerar com o modelo: {model_name}")
    model = genai.GenerativeModel(f'models/{model_name}')
    prompt_parts = [style_prompt, text_to_narrate]
    config = genai.types.GenerationConfig(
        speech=genai.types.SpeechConfig(
            voice=voice_name
        )
    )
    response = model.generate_content(prompt_parts, generation_config=config, stream=False)
    audio_part = response.candidates[0].content.parts[0]
    audio_data = audio_part.inline_data.data
    return base64.b64encode(audio_data).decode('utf-8')

@app.route('/generate', methods=['POST'])
def generate_audio_endpoint():
    # A verificação de segurança foi removida para este teste
    
    data = request.get_json()
    if not data: return jsonify({"error": "Requisição JSON inválida"}), 400

    text, style, voice = data.get('text'), data.get('style'), data.get('voice')

    if not all([text, style, voice]):
        return jsonify({"error": "Dados incompletos"}), 400

    model_to_use_name = "Pro"
    try:
        audio_base64 = generate_audio_from_model("gemini-2.5-pro-preview-tts", style, text, voice)
    except Exception as e:
        print(f"INFO: Erro com o modelo Pro: {e}. Tentando com o modelo Flash.")
        model_to_use_name = "Flash"
        try:
            audio_base64 = generate_audio_from_model("gemini-2.5-flash-preview-tts", style, text, voice)
        except Exception as e_flash:
            print(f"ERRO: Falha com ambos os modelos. Detalhe: {e_flash}")
            return jsonify({"error": f"Falha ao se comunicar com a API do Google: {e_flash}"}), 502

    return jsonify({"success": True, "model_used": model_to_use_name, "audio_data": audio_base64})

@app.route('/')
def home():
    return "Serviço de Geração de Áudio (Modo de Acesso Aberto) - Online"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
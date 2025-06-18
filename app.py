import os
import base64
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)

# --- Configuração das Chaves ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY") # Chave para proteger nosso próprio serviço

# Configura o cliente da API do Google
genai.configure(api_key=GEMINI_API_KEY)

def generate_audio_from_model(model_name, style_prompt, text_to_narrate, voice_name):
    """Gera áudio usando a biblioteca oficial do Google."""
    print(f"INFO: Tentando gerar com o modelo: {model_name}")
    model = genai.GenerativeModel(f'models/{model_name}')
    response = model.generate_content([style_prompt, text_to_narrate], stream=False)
    audio_part = response.candidates[0].content.parts[0]
    audio_data = audio_part.inline_data.data
    return base64.b64encode(audio_data).decode('utf-8')

@app.route('/generate', methods=['POST'])
def generate_audio_endpoint():
    # 1. Segurança: Verifica nossa chave secreta interna
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {INTERNAL_API_KEY}":
        print(f"ERRO: Tentativa de acesso não autorizada. Cabeçalho recebido: {auth_header}")
        return jsonify({"error": "Acesso não autorizado"}), 401

    data = request.get_json()
    if not data: return jsonify({"error": "Requisição JSON inválida"}), 400

    text = data.get('text')
    style = data.get('style')
    voice = data.get('voice')

    if not all([text, style, voice]):
        return jsonify({"error": "Dados incompletos"}), 400

    # 2. Lógica de Failover
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

    # 3. Resposta de Sucesso
    print("INFO: Áudio gerado com sucesso.")
    return jsonify({
        "success": True,
        "model_used": model_to_use_name,
        "audio_data": audio_base64
    })

@app.route('/')
def home():
    return "Serviço de Geração de Áudio - Online"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
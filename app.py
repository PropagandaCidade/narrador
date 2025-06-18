import os
import io
import base64
from flask import Flask, request, jsonify, make_response
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import content_types

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# --- Configuração das Chaves de API ---
# Pega as chaves das variáveis de ambiente
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

# Configura o cliente da API do Google
genai.configure(api_key=GEMINI_API_KEY)

# --- Função de Geração de Áudio ---
def generate_audio_from_model(model_name, style_prompt, text_to_narrate, voice_name):
    """
    Gera áudio usando um modelo Gemini específico.
    Retorna o áudio em base64 e o nome do modelo usado.
    """
    print(f"Tentando gerar com o modelo: {model_name}")
    model = genai.GenerativeModel(model_name)
    
    # Monta o prompt
    prompt_parts = [
        style_prompt,
        text_to_narrate
    ]
    
    # Faz a chamada à API usando a biblioteca oficial
    response = model.generate_content(prompt_parts, stream=False)
    
    # Extrai o áudio da resposta
    audio_part = response.candidates[0].content.parts[0]
    audio_data = audio_part.inline_data.data
    
    # Codifica o áudio em base64 para enviar via JSON
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    return audio_base64

# --- Rota Principal da API ---
@app.route('/generate', methods=['POST'])
def generate_audio_endpoint():
    # 1. Segurança: Verifica a chave de API interna
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {INTERNAL_API_KEY}":
        return jsonify({"error": "Acesso não autorizado ao serviço de áudio"}), 401

    # 2. Pega os dados da requisição JSON
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição JSON inválida"}), 400

    text = data.get('text')
    style = data.get('style')
    voice = data.get('voice')

    if not all([text, style, voice]):
        return jsonify({"error": "Dados incompletos: text, style, e voice são obrigatórios"}), 400

    # 3. Lógica de Failover
    model_to_use_name = "Pro"
    try:
        # Tenta com o modelo Pro
        audio_base64 = generate_audio_from_model(
            "models/gemini-2.5-pro-preview-tts",
            style,
            text,
            voice
        )
    except Exception as e:
        print(f"Erro com o modelo Pro: {e}. Tentando com o modelo Flash.")
        # Se falhar (ex: cota), tenta com o modelo Flash
        model_to_use_name = "Flash"
        try:
            audio_base64 = generate_audio_from_model(
                "models/gemini-2.5-flash-preview-tts",
                style,
                text,
                voice
            )
        except Exception as e_flash:
            print(f"Erro com o modelo Flash também: {e_flash}")
            return jsonify({"error": f"Falha ao gerar áudio com ambos os modelos. Detalhe: {e_flash}"}), 500

    # 4. Retorna a resposta de sucesso em formato JSON
    return jsonify({
        "success": True,
        "model_used": model_to_use_name,
        "audio_data": audio_base64
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
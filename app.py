import os
import base64
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)

# --- Configuração e Verificação das Chaves ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

# Verificação crucial na inicialização do servidor
if not GEMINI_API_KEY or not INTERNAL_API_KEY:
    # Se as chaves não forem encontradas, o servidor não deve nem iniciar.
    # Isso aparecerá nos logs do Render se houver um problema.
    raise SystemExit("ERRO CRÍTICO: Variáveis de ambiente GEMINI_API_KEY ou INTERNAL_API_KEY não encontradas.")

# **A LINHA MAIS IMPORTANTE**
# Configura o cliente da API do Google para todas as chamadas subsequentes.
genai.configure(api_key=GEMINI_API_KEY)


def generate_audio_from_model(model_name, style_prompt, text_to_narrate, voice_name):
    """Gera áudio usando a biblioteca oficial do Google."""
    print(f"INFO: Tentando gerar com o modelo: {model_name}")
    
    # A biblioteca Python usa o nome completo do modelo com o prefixo 'models/'
    model = genai.GenerativeModel(f'models/{model_name}')
    
    # O prompt correto para a biblioteca Python é um array de strings
    prompt_parts = [style_prompt, text_to_narrate]
    
    # A configuração da voz e da resposta é feita no 'generation_config'
    # Esta é a estrutura correta para a biblioteca, diferente da API REST
    config = genai.types.GenerationConfig(
        speech=genai.types.SpeechConfig(
            voice=voice_name
        )
    )

    # Faz a chamada à API usando a biblioteca oficial
    response = model.generate_content(prompt_parts, generation_config=config, stream=False)
    
    audio_part = response.candidates[0].content.parts[0]
    audio_data = audio_part.inline_data.data
    
    # Codifica o áudio em base64 para enviar via JSON
    return base64.b64encode(audio_data).decode('utf-8')


@app.route('/generate', methods=['POST'])
def generate_audio_endpoint():
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {INTERNAL_API_KEY}":
        return jsonify({"error": "Acesso não autorizado"}), 401

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
            # Retorna o erro específico da API do Google
            return jsonify({"error": f"Falha ao se comunicar com a API do Google: {e_flash}"}), 502

    return jsonify({"success": True, "model_used": model_to_use_name, "audio_data": audio_base64})


@app.route('/')
def home():
    return "Serviço de Geração de Áudio - Online"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google.cloud import texttospeech

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/generate": {"origins": "*"}})  # Permite requisições do frontend (substitua "*" pelo domínio da Hostinger em produção)

# Configuração da chave API do Google Cloud
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not GOOGLE_APPLICATION_CREDENTIALS or not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
    raise SystemExit("ERRO CRÍTICO: GOOGLE_APPLICATION_CREDENTIALS não encontrada ou inválida.")

# Inicializa o cliente da Text-to-Speech API
client = texttospeech.TextToSpeechClient()

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
        # Configura o texto de entrada (concatena estilo e texto)
        input_text = texttospeech.SynthesisInput(text=f"{style} {text}")

        # Configura a voz (usando uma voz padrão se 'charon' ou 'aoede' não forem suportadas)
        voice_config = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice if voice in ["charon", "aoede"] else "en-US-Wavenet-D"  # Fallback para uma voz padrão
        )

        # Configura o formato de áudio
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000
        )

        # Gera o áudio
        response = client.synthesize_speech(
            input=input_text,
            voice=voice_config,
            audio_config=audio_config
        )

        # Converte o áudio para base64
        audio_data = response.audio_content
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        return jsonify({
            "success": True,
            "model_used": "Google Text-to-Speech",
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
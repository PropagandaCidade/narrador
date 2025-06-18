import os
import base64
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from gtts import gTTS
from pydub import AudioSegment

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/generate": {"origins": "*"}})  # Permite requisições do frontend (substitua "*" pelo domínio da Hostinger em produção)

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
        # Configura o idioma e a velocidade com base no estilo
        lang = "en"  # Padrão para inglês, ajustável conforme necessidade
        slow = "slow" in style.lower()  # Define velocidade lenta se "slow" estiver no estilo

        # Gera o áudio com gTTS
        tts = gTTS(text=text, lang=lang, slow=slow)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        # Converte MP3 para WAV
        audio = AudioSegment.from_mp3(mp3_fp)
        wav_fp = io.BytesIO()
        audio.export(wav_fp, format="wav")
        wav_fp.seek(0)

        # Converte para base64
        audio_data = wav_fp.read()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        return jsonify({
            "success": True,
            "model_used": "gTTS",
            "audio_data": audio_base64
        })

    except Exception as e:
        error_message = f"Falha na geração de áudio: {str(e)}"
        print(f"ERRO: {error_message}")
        return jsonify({"error": error_message}), 502

@app.route('/')
def home():
    return "Serviço de Geração de Áudio - Online"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
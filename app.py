import os
import base64
import struct
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/generate": {"origins": "*"}})  # Permite requisições do frontend (substitua "*" pelo domínio da Hostinger em produção)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise SystemExit("ERRO CRÍTICO: GEMINI_API_KEY não encontrada.")
genai.configure(api_key=GEMINI_API_KEY)

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1,
        num_channels, sample_rate, byte_rate, block_align,
        bits_per_sample, b"data", data_size
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

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
        prompt = f"Generate audio narration with a {style} using voice {voice}: {text}"
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "audio/wav"  # Configura para áudio, conforme modalidade suportada
            }
        )

        # Verifica se a resposta contém dados de áudio
        if not response.candidates or not response.candidates[0].content.parts or not response.candidates[0].content.parts[0].inline_data:
            raise ValueError("A API não retornou dados de áudio na resposta.")

        audio_data = response.candidates[0].content.parts[0].inline_data.data
        mime_type = response.candidates[0].content.parts[0].inline_data.mime_type

        # Converte para WAV, se necessário
        if mime_type != "audio/wav":
            audio_data = convert_to_wav(audio_data, mime_type)

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
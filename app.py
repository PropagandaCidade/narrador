import os
import struct
import base64
import io

from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Função para converter áudio em WAV
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

# Função auxiliar para interpretar o tipo MIME do áudio
def parse_audio_mime_type(mime_type: str) -> dict:
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

@app.route('/')
def home():
    return "Backend do Gerador de Narração está online."

@app.route('/generate-audio', methods=['POST', 'OPTIONS'])
def generate_audio_endpoint():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        headers = response.headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        headers['Access-Control-Allow-Methods'] = 'POST,OPTIONS'
        return response

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERRO: Variável de ambiente GEMINI_API_KEY não encontrada.")
        return jsonify({"error": "Chave da API ausente."}), 500

    data = request.get_json()
    text_to_narrate = data.get('text')
    voice_name = data.get('voice')
    style_instructions_text = data.get('style')

    if not text_to_narrate:
        return jsonify({"error": "O texto não pode estar vazio."}), 400
    if not voice_name:
        return jsonify({"error": "A voz não pode estar vazia."}), 400

    try:
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")

        generation_config = GenerationConfig(
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_mime_type="audio/wav"
        )

        voice_config = VoiceConfig(
            name=voice_name,
            language_code="pt-BR"
        )

        audio_config = AudioConfig(
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=0.0
        )

        parts = [text_to_narrate]
        if style_instructions_text:
            parts.insert(0, style_instructions_text)

        response = model.generate_content(
            contents=parts,
            generation_config=generation_config,
            safety_settings=[],
            stream=False,
            request_options={}
        )

        if not response or not response.candidates or not response.audio:
            return jsonify({"error": "Não foi possível gerar o áudio."}), 500

        wav_data = convert_to_wav(response.audio.data, response.audio.mime_type)
        audio_b64 = base64.b64encode(wav_data).decode()

        response_json = jsonify({
            "audio_data": audio_b64,
            "model_used": "gemini-1.5-flash-latest"
        })

        response_json.headers.add("Access-Control-Allow-Origin", "*")
        return response_json

    except Exception as e:
        print(f"Erro ao gerar áudio: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
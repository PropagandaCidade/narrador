# app.py - VERSÃO LEVE E FUNCIONAL PARA SEU NOVO SERVIÇO

import os
import base64
import struct
import io
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydub import AudioSegment

# --- Configuração Inicial ---
load_dotenv()

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("ERRO: GEMINI_API_KEY não definida.")

# --- Funções ---

def sanitize_and_normalize_text(text):
    if not isinstance(text, str): text = str(text)
    text = re.sub(r'R\$\s*([\d,.]+)', r'\1 reais', text)
    text = re.sub(r'(\d+)\s*[xX]', r'\1 vezes ', text)
    text = re.sub(r'\s*[-–—]\s*', ', ', text)
    return re.sub(r'[^\w\s.,!?áéíóúâêîôûãõàèìòùçÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ]', '', text).strip()

def convert_to_wav(audio_ bytes, mime_type: str) -> bytes:
    rate = 24000
    if mime_type and "rate=" in mime_type:
        try: rate = int(mime_type.split("rate=")[1].split(";")[0])
        except: pass
    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(audio_data), b"WAVE", b"fmt ", 16, 1, 1, rate, rate * 2, 2, 16, b"data", len(audio_data))
    return header + audio_data

@app.route('/')
def home():
    return "Narrador Virtual está online!"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    data = request.get_json()
    if not  return jsonify({"error": "JSON inválido."}), 400
    text = data.get('text')
    voice_id = data.get('voiceId')
    if not text or not voice_id: return jsonify({"error": "text e voiceId obrigatórios."}), 400

    try:
        normalized_text = sanitize_and_normalize_text(text)
        print(f"[INFO] Texto recebido: {len(normalized_text)} caracteres")

        client = genai.Client(api_key=API_KEY)
        model = "gemini-2.5-pro-preview-tts"
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=normalized_text)])]
        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_id)
                )
            )
        )

        full_audio_data = bytearray()
        stream = client.models.generate_content_stream(model=model, contents=contents, config=config)
        for response in stream:
            if response.candidates and response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.
                    full_audio_data.extend(part.inline_data.data)

        if not full_audio_
            return jsonify({"error": "Nenhum áudio gerado."}), 500

        wav_data = convert_to_wav(bytes(full_audio_data), "audio/L16;rate=24000")
        audio_segment = AudioSegment.from_file(io.BytesIO(wav_data), format="wav")

        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="128k")
        mp3_data = mp3_buffer.getvalue()

        audio_base64 = base64.b64encode(mp3_data).decode('utf-8')
        return jsonify({"audioContent": audio_base64})

    except Exception as e:
        print(f"ERRO: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
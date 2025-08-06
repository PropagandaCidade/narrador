# app.py - VERSÃO FINAL, CORRIGIDA E FUNCIONAL

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
    raise ValueError("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida.")

# --- Funções de Suporte ---

def sanitize_and_normalize_text(text):
    if not isinstance(text, str): text = str(text)
    text = re.sub(r'R\$\s*([\d,.]+)', lambda m: m.group(1).replace('.', '').replace(',', ' vírgula ') + ' reais', text)
    text = re.sub(r'(\d+)\s*[xX](?!\w)', r'\1 vezes ', text)
    text = re.sub(r'\s*[-–—]\s*', ', ', text)
    text = re.sub(r'[^\w\s.,!?áéíóúâêîôûãõàèìòùçÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Converte dados de áudio cru em formato WAV com cabeçalho válido."""
    # Extrai a taxa de amostragem do MIME type
    rate = 24000
    if mime_type and "rate=" in mime_type:
        try:
            rate = int(mime_type.split("rate=")[1].split(";")[0])
        except (ValueError, IndexError):
            pass
    # Parâmetros fixos
    bits_per_sample = 16
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = rate * block_align
    chunk_size = 36 + data_size
    # Cabeçalho WAV (RIFF)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16,
        1, num_channels, rate, byte_rate,
        block_align, bits_per_sample, b"data", data_size
    )
    return header + audio_data

# --- Rotas da API ---

@app.route('/')
def home():
    return "Serviço de Narração está online (v9.0 - Corrigido)."

@app.route('/health')
def health_check():
    return "API de Narração está saudável.", 200

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    data = request.get_json()
    if not  return jsonify({"error": "Requisição JSON inválida."}), 400
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId')
    if not text_to_speak or not voice_id: return jsonify({"error": "Os campos 'text' e 'voiceId' são obrigatórios."}), 400
    try:
        normalized_text = sanitize_and_normalize_text(text_to_speak)
        print(f"[INFO] Texto recebido: {len(normalized_text)} caracteres")
        client = genai.Client(api_key=API_KEY)
        model_name = "gemini-2.5-pro-preview-tts"
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=normalized_text)])]
        generation_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_id)
                )
            )
        )
        full_audio_data = bytearray()
        audio_mime_type = "audio/L16;rate=24000"
        stream = client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=generation_config
        )
        for response in stream:
            if response.candidates and response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    full_audio_data.extend(part.inline_data.data)
                    if part.inline_data.mime_type:
                        audio_mime_type = part.inline_data.mime_type
        if not full_audio_data:
            return jsonify({"error": "Nenhum áudio foi gerado."}), 500
        wav_data = convert_to_wav(bytes(full_audio_data), audio_mime_type)
        audio_segment = AudioSegment.from_file(io.BytesIO(wav_data), format="wav")
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="128k")
        mp3_data = mp3_buffer.getvalue()
        audio_base64 = base64.b64encode(mp3_data).decode('utf-8')
        return jsonify({"audioContent": audio_base64})
    except Exception as e:
        print(f"ERRO INESPERADO: {e}")
        return jsonify({"error": str(e)}), 500

# --- Execução ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
# app.py - Versão para Railway
import os
import io
import struct
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS # Importe CORS
from google import genai
from google.genai import types

app = Flask(__name__)

# --- CONFIGURAÇÃO DE CORS AJUSTADA ---
# Permite requisições especificamente do seu domínio frontend
CORS(app, resources={r"/api/*": {"origins": "https://propagandacidadeaudio.com.br"}}, expose_headers=['X-Model-Used'])
# --- FIM DA CONFIGURAÇÃO DE CORS ---

# Função convert_to_wav (como fornecida anteriormente)
def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    rate = 24000
    bits_per_sample = 16
    if mime_type and "rate=" in mime_type:
        try:
            rate = int(mime_type.split("rate=")[1].split(";")[0])
        except (ValueError, IndexError):
            pass
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = rate * block_align
    chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16,
        1, num_channels, rate, byte_rate,
        block_align, bits_per_sample, b"data", data_size
    )
    return header + audio_data

@app.route('/')
def home():
    return "Serviço de Narração no Railway está online!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    api_key = os.environ.get("GEMINI_API_KEY")
    # A checagem de api_key foi removida pois a variável de ambiente já é configurada no Railway.

    data = request.get_json()
    print(f"Dados recebidos do frontend: {data}") # Log para depuração

    if data is None: # Valida se o corpo JSON foi recebido corretamente
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')
    style_instructions_text = data.get('style', '')

    if not text_to_narrate: # Valida se 'text' está presente e não vazio
        return jsonify({"error": "O campo 'text' não pode estar vazio."}), 400
    if not voice_name: # Valida se 'voice' está presente e não vazio
        return jsonify({"error": "O campo 'voice' não pode estar vazio."}), 400

    try:
        client = genai.Client(api_key=api_key)
        model = "gemini-2.5-pro-preview-tts"

        parts_list = []
        if style_instructions_text:
            parts_list.append(types.Part.from_text(text=style_instructions_text))
        parts_list.append(types.Part.from_text(text=text_to_narrate))
        contents = [types.Content(role="user", parts=parts_list)]

        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        )

        audio_buffer = bytearray()
        audio_mime_type = "audio/L16;rate=24000"

        stream = client.models.generate_content_stream(model=model, contents=contents, config=generate_content_config)

        for chunk in stream:
            if (chunk.candidates and
                chunk.candidates[0].content and
                chunk.candidates[0].content.parts and
                chunk.candidates[0].content.parts[0].inline_data and
                chunk.candidates[0].content.parts[0].inline_data.data):
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_buffer.extend(inline_data.data)
                if inline_data.mime_type:
                    audio_mime_type = inline_data.mime_type

        if not audio_buffer:
            return jsonify({"error": "Não foi possível gerar o áudio."}), 500

        wav_data = convert_to_wav(bytes(audio_buffer), audio_mime_type)
        response = make_response(send_file(io.BytesIO(wav_data), mimetype='audio/wav', as_attachment=False))
        response.headers['X-Model-Used'] = "Pro"
        return response

    except Exception as e:
        print(f"Ocorreu um erro na API: {e}")
        return jsonify({"error": f"Erro ao contatar a API do Google Gemini: {e}"}), 500

if __name__ == '__main__':
    # Para execução local com `python app.py`
    # O Railway irá configurar a porta via variável de ambiente PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
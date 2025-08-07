# app.py - VERSÃO CORRIGIDA E ADAPTADA AO SEU PROJETO
import os
import io
import struct
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# --- IMPORTAÇÃO CORRETA E DEFINITIVA ---
# Esta é a única forma que funciona de maneira estável.
import google.generativeai as genai
from google.generativeai import types

app = Flask(__name__)

# Sua configuração de CORS que já funcionava
CORS(app)

# --- Suas funções auxiliares (convert_to_wav) ---
# Mantemos suas funções, pois a lógica de streaming do exemplo precisa delas.
def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    rate = 24000
    if mime_type and "rate=" in mime_type:
        try:
            rate_str = mime_type.split("rate=")[1].split(";")[0]
            rate = int(rate_str)
        except (ValueError, IndexError):
            pass
    return {"rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    parameters = parse_audio_mime_type(mime_type)
    sample_rate = parameters["rate"]
    bits_per_sample = 16
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16,
        1, num_channels, sample_rate, byte_rate,
        block_align, bits_per_sample, b"data", data_size
    )
    return header + audio_data

# --- Fim das funções auxiliares ---

@app.route('/')
def home():
    return "Serviço de Narração no Railway está online!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    # Mantemos sua lógica de obter dados, que está correta
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Chave de API do servidor não configurada."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')

    if not text_to_narrate or not voice_name:
        return jsonify({"error": "Os campos 'text' e 'voice' são obrigatórios."}), 400

    try:
        # --- LÓGICA DO EXEMPLO DO GOOGLE ADAPTADA AQUI ---
        client = genai.Client(api_key=api_key)
        model = "gemini-2.5-pro-preview-tts"
        
        # O exemplo do Google usa types.Part, vamos seguir.
        contents = [types.Part.from_text(text=text_to_narrate)]

        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )

        audio_buffer = bytearray()
        audio_mime_type = "audio/L16;rate=24000"

        stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        for chunk in stream:
            if (chunk.candidates and chunk.candidates[0].content and
                chunk.candidates[0].content.parts[0].inline_data and
                chunk.candidates[0].content.parts[0].inline_data.data):
                
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_buffer.extend(inline_data.data)
                if inline_data.mime_type:
                    audio_mime_type = inline_data.mime_type

        if not audio_buffer:
            return jsonify({"error": "Não foi possível gerar o áudio."}), 500

        wav_data = convert_to_wav(bytes(audio_buffer), audio_mime_type)
        
        # Sua lógica de resposta, que já funcionava
        http_response = make_response(send_file(
            io.BytesIO(wav_data),
            mimetype='audio/wav',
            as_attachment=False
        ))
        http_response.headers['X-Model-Used'] = "Pro"
        return http_response

    except Exception as e:
        error_message = f"Erro ao contatar a API do Google Gemini: {e}"
        print(f"ERRO CRÍTICO NA API: {error_message}")
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
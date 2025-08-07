# app.py - VERSÃO FINAL adaptada do seu código funcional do Colab
import os
import io
import struct
import re
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# --- IMPORTAÇÃO CORRETA E DEFINITIVA ---
import google.generativeai as genai
from google.generativeai import types

app = Flask(__name__)
CORS(app) 

# --- SUAS FUNÇÕES AUXILIARES DO COLAB (JÁ ESTÃO CORRETAS) ---
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
    """Rota simples para verificar se o serviço está online."""
    return "Serviço de Narração no Railway está online e pronto!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Rota que gera o áudio, adaptada do seu código do Colab."""
    
    # --- 1. ADAPTAÇÃO: Obter a Chave da API do Ambiente do Railway ---
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Chave da API não configurada no Railway."}), 500

    # --- 2. Obter os Dados da Requisição (seu código, já correto) ---
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')
    style_instructions_text = data.get('style', '')

    if not text_to_narrate or not voice_name:
        return jsonify({"error": "Os campos 'text' e 'voice' são obrigatórios."}), 400

    try:
        # --- 3. TODA A LÓGICA DE GERAÇÃO É DO SEU CÓDIGO FUNCIONAL ---
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

        stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config
        )

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
            return jsonify({"error": "A API do Google não retornou dados de áudio."}), 500

        wav_data = convert_to_wav(bytes(audio_buffer), audio_mime_type)

        response = make_response(send_file(
            io.BytesIO(wav_data),
            mimetype='audio/wav',
            as_attachment=False
        ))
        response.headers['X-Model-Used'] = "Pro"
        return response

    except Exception as e:
        print(f"Ocorreu um erro na API: {e}")
        return jsonify({"error": f"Erro ao contatar a API do Google Gemini: {e}"}), 500

# --- Ponto de Entrada para o Servidor do Railway (Gunicorn) ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
# app.py - VERSÃO FINAL E DEFINITIVA
import os
import io
import struct
import re
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Importação correta e única necessária
import google.generativeai as genai
from google.generativeai import types

app = Flask(__name__)
CORS(app) 

# --- Suas funções auxiliares do Colab (JÁ ESTÃO CORRETAS) ---
def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    rate = 24000
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
    """Rota que gera o áudio, combinando a lógica do Colab com a inicialização correta."""
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Chave da API não configurada no Railway."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')
    style_instructions_text = data.get('style', '')

    if not text_to_narrate or not voice_name:
        return jsonify({"error": "Os campos 'text' e 'voice' são obrigatórios."}), 400

    try:
        # --- A INICIALIZAÇÃO CORRETA PARA A BIBLIOTECA 0.8.5 ---
        genai.configure(api_key=api_key)
        
        # O modelo TTS correto
        tts_model = genai.GenerativeModel(model_name='models/text-to-speech')
        
        # --- A LÓGICA DE GERAÇÃO DETALHADA (do seu código do Colab) ---
        contents = [text_to_narrate]
        
        generation_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )

        print(f"Gerando áudio para: '{text_to_narrate[:50]}...' com voz: '{voice_name}'")

        response = tts_model.generate_content(
            contents=contents,
            config=generation_config
        )
        
        audio_part = response.candidates[0].content.parts[0]
        wav_data = audio_part.inline_data.data
        
        if not wav_data:
            return jsonify({"error": "A API do Google não retornou dados de áudio."}), 500
        
        # A resposta final
        final_response = make_response(send_file(
            io.BytesIO(wav_data),
            mimetype='audio/wav',
            as_attachment=False
        ))
        final_response.headers['X-Model-Used'] = "Pro"
        return final_response

    except Exception as e:
        print(f"Ocorreu um erro na API: {e}")
        return jsonify({"error": f"Erro ao contatar a API do Google Gemini: {e}"}), 500

# --- Ponto de Entrada para o Servidor do Railway (Gunicorn) ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
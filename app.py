# app.py - VERSÃO FINAL E CORRIGIDA
import os
import io
import struct
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Importações corretas para a API do Gemini
import google.generativeai as genai
from google.generativeai import types

app = Flask(__name__)

# Configuração de CORS que já está funcionando
CORS(app) 

# Suas funções auxiliares, que a lógica de streaming precisa
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

@app.route('/')
def home():
    """Rota para verificar se o serviço está online."""
    return "Serviço de Narração no Railway está online e estável!"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Endpoint principal que gera o áudio usando o método de baixo nível oficial."""
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
        genai.configure(api_key=api_key)
        
        tts_model = genai.GenerativeModel(model_name='models/text-to-speech')

        print(f"Gerando áudio para: '{text_to_narrate[:50]}...' com voz: '{voice_name}'")

        # --- A CORREÇÃO FINAL ESTÁ AQUI ---
        # A API espera uma string "audio", não uma constante.
        generation_config = types.GenerateContentConfig(
            response_modalities=["audio"], # <-- ESTA É A LINHA CORRIGIDA
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        response = tts_model.generate_content(
            contents=[text_to_narrate],
            config=generation_config
        )
        
        audio_part = response.candidates[0].content.parts[0]
        wav_data = audio_part.inline_data.data
        
        if not wav_data:
            return jsonify({"error": "Não foi possível gerar o áudio."}), 500
        
        http_response = make_response(send_file(
            io.BytesIO(wav_data),
            mimetype='audio/wav',
            as_attachment=False
        ))
        http_response.headers['X-Model-Used'] = "Pro"
        
        print("Sucesso: Áudio gerado e enviado ao cliente.")
        return http_response

    except Exception as e:
        error_message = f"Erro ao contatar a API do Google Gemini: {e}"
        print(f"ERRO CRÍTICO NA API: {error_message}")
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
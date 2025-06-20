import os
import struct
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
# Configuração de CORS que sabemos que funciona e é necessária
CORS(app, origins="*", expose_headers=['X-Model-Used'])

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Função original para converter para WAV, se necessário (embora peçamos MP3)."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters.get("bits_per_sample", 16)
    sample_rate = parameters.get("rate", 24000)
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

def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """Função original para analisar o MIME type."""
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError): pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError): pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

@app.route('/')
def home():
    return "Backend do Estúdio Virtual está online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Configuração do servidor incompleta"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida"}), 400

    text_to_narrate = data.get('text')
    voice_name = data.get('voice')
    style_instructions_text = data.get('style')

    if not text_to_narrate:
        return jsonify({"error": "O texto não pode estar vazio."}), 400

    client = genai.Client(api_key=api_key)
    
    parts_list = []
    if style_instructions_text:
        parts_list.append(types.Part.from_text(text=style_instructions_text))
    parts_list.append(types.Part.from_text(text=text_to_narrate))
    contents = [types.Content(role="user", parts=parts_list)]
    
    # Configuração de Geração que funciona
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["audio/mp3"]
    )
    speech_config = types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
        )
    )

    models_to_try = [
        ("Pro", "gemini-2.5-pro-preview-tts"),
        ("Flash", "gemini-2.5-flash-preview-tts")
    ]
    
    audio_data = None
    model_used = "Nenhum"

    for friendly_name, model_name in models_to_try:
        try:
            print(f"Tentando gerar com o modelo: {model_name}")
            # Usando a chamada generate_content que é mais flexível
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=generate_content_config,
                speech_config=speech_config
            )
            
            if response.candidates and response.candidates[0].content.parts:
                audio_data = response.candidates[0].content.parts[0].inline_data.data
                model_used = friendly_name
                print(f"Sucesso com o modelo {friendly_name}!")
                break # Sai do loop se a geração foi bem-sucedida
            
        except Exception as e:
            # Verifica se o erro é de cota para decidir se continua
            if "resource_exhausted" in str(e).lower() or "quota" in str(e).lower():
                print(f"Cota do modelo {friendly_name} esgotada. Tentando o próximo.")
                continue # Continua para o próximo modelo na lista
            else:
                # Se for outro tipo de erro, para e retorna o erro
                print(f"Erro inesperado com o modelo {friendly_name}: {e}")
                return jsonify({"error": f"Erro na API do Gemini: {e}"}), 500
    
    if not audio_data:
        return jsonify({"error": "Não foi possível gerar o áudio com nenhum dos modelos disponíveis."}), 500

    # Cria a resposta e envia o áudio MP3
    response_http = make_response(send_file(io.BytesIO(audio_data), mimetype='audio/mp3'))
    response_http.headers['X-Model-Used'] = model_used
    return response_http
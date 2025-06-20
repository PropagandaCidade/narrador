import os
import struct
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

# Inicializa a aplicação Flask
app = Flask(__name__)

# Configura o CORS para ser mais permissivo e resolver o erro de acesso
# origins="*" permite que qualquer site (incluindo o seu na Hostinger) faça requisições.
# expose_headers permite que o JavaScript leia o nosso cabeçalho customizado.
CORS(app, origins="*", expose_headers=['X-Model-Used'])

# --- FUNÇÕES AUXILIARES ---

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Gera um cabeçalho WAV para os dados de áudio brutos."""
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

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """Extrai bits por amostra e taxa de amostragem do MIME type."""
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

def generate_audio_from_model(client, model_name, contents, config):
    """Função auxiliar para gerar áudio com um modelo específico."""
    print(f"Tentando gerar áudio com o modelo: {model_name}")
    audio_buffer = bytearray()
    audio_mime_type = "audio/L16;rate=24000"
    
    stream = client.models.generate_content_stream(model=model_name, contents=contents, config=config)
    
    for chunk in stream:
        if (chunk.candidates and chunk.candidates[0].content and
            chunk.candidates[0].content.parts and chunk.candidates[0].content.parts[0].inline_data and
            chunk.candidates[0].content.parts[0].inline_data.data):
            inline_data = chunk.candidates[0].content.parts[0].inline_data
            audio_buffer.extend(inline_data.data)
            audio_mime_type = inline_data.mime_type
    
    if not audio_buffer:
        raise Exception(f"Não foi possível gerar dados de áudio com o modelo {model_name}.")
        
    return convert_to_wav(bytes(audio_buffer), audio_mime_type)


# --- ROTAS DA API ---

@app.route('/')
def home():
    """Rota principal para verificar se o backend está online."""
    return "Backend do Estúdio de Narração Virtual está online."

@app.route('/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Rota principal que recebe o texto e gera o áudio."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Configuração do servidor incompleta: Chave da API ausente."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400
        
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
    
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        ),
    )

    model_to_use = "Pro"
    try:
        # 1. Tenta com o modelo PRO (Premium)
        wav_data = generate_audio_from_model(client, "gemini-2.5-pro-preview-tts", contents, generate_content_config)
        print("Sucesso com o modelo Pro!")
        
    except google_exceptions.ResourceExhausted as e:
        # 2. Se a cota do Pro esgotar, tenta com o modelo FLASH (Failover)
        print(f"Cota do modelo Pro esgotada. Tentando com o modelo Flash. Erro original: {e}")
        model_to_use = "Flash"
        try:
            wav_data = generate_audio_from_model(client, "gemini-2.5-flash-preview-tts", contents, generate_content_config)
            print("Sucesso com o modelo Flash (failover)!")
        except Exception as e_flash:
            print(f"Falha também com o modelo Flash. Erro: {e_flash}")
            return jsonify({"error": f"Ambos os modelos de narração estão indisponíveis. Erro: {e_flash}"}), 500
    
    except Exception as e:
        print(f"Ocorreu um erro inesperado com o modelo Pro: {e}")
        return jsonify({"error": f"Erro ao contatar a API do Gemini: {e}"}), 500

    # Cria a resposta de arquivo de áudio
    response = make_response(send_file(io.BytesIO(wav_data), mimetype='audio/wav', as_attachment=False))
    # Adiciona o cabeçalho customizado com o nome do modelo usado
    response.headers['X-Model-Used'] = model_to_use
    
    return response
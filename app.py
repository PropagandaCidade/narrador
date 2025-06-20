import os
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
# Configuração de CORS que sabemos que funciona e é necessária
CORS(app, origins="*", expose_headers=['X-Model-Used'])

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
    
    # Prepara o conteúdo, exatamente como na sua versão funcional
    parts_list = []
    if style_instructions_text:
        parts_list.append(types.Part.from_text(text=style_instructions_text))
    parts_list.append(types.Part.from_text(text=text_to_narrate))
    contents = [types.Content(role="user", parts=parts_list)]
    
    # Configuração da geração, pedindo MP3 para simplificar
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["audio/mp3"], # MUDANÇA: Pedindo MP3 em vez de WAV
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        )
    )

    models_to_try = [
        ("Pro", "gemini-2.5-pro-preview-tts"),
        ("Flash", "gemini-2.5-flash-preview-tts")
    ]
    
    audio_buffer = None
    model_used = "Nenhum"

    for friendly_name, model_name in models_to_try:
        try:
            print(f"Tentando gerar com o modelo: {model_name}")
            # Usando a sua lógica de streaming funcional
            stream = client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=generate_content_config
            )
            
            temp_buffer = bytearray()
            for chunk in stream:
                if (chunk.candidates and chunk.candidates[0].content and
                    chunk.candidates[0].content.parts and chunk.candidates[0].content.parts[0].inline_data and
                    chunk.candidates[0].content.parts[0].inline_data.data):
                    temp_buffer.extend(chunk.candidates[0].content.parts[0].inline_data.data)

            # Se o buffer foi preenchido, a geração foi um sucesso
            if temp_buffer:
                audio_buffer = temp_buffer
                model_used = friendly_name
                print(f"Sucesso com o modelo {friendly_name}!")
                break # Sai do loop se a geração foi bem-sucedida
            
        except Exception as e:
            if "resource_exhausted" in str(e).lower() or "quota" in str(e).lower():
                print(f"Cota do modelo {friendly_name} esgotada. Tentando o próximo.")
                continue # Continua para o próximo modelo na lista
            else:
                print(f"Erro inesperado com o modelo {friendly_name}: {e}")
                # Não retorna erro aqui, permite que tente o próximo modelo se houver
    
    if not audio_buffer:
        return jsonify({"error": "Não foi possível gerar o áudio com nenhum dos modelos disponíveis."}), 500

    # Cria a resposta e envia o áudio MP3
    response = make_response(send_file(io.BytesIO(audio_buffer), mimetype='audio/mp3'))
    response.headers['X-Model-Used'] = model_used
    return response
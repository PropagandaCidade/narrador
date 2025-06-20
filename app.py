import os
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app, origins="*", expose_headers=['X-Model-Used'])

# --- ROTAS DA API ---
@app.route('/')
def home():
    return "Backend do Estúdio Virtual está online. Versão 2.0"

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
        return jsonify({"error": "O texto não pode estar vazio"}), 400

    client = genai.Client(api_key=api_key)
    
    # Define os modelos a serem tentados
    model_pro = "gemini-2.5-pro-preview-tts"
    model_flash = "gemini-2.5-flash-preview-tts"
    
    parts_list = []
    if style_instructions_text:
        parts_list.append(types.Part.from_text(text=style_instructions_text))
    parts_list.append(types.Part.from_text(text=text_to_narrate))
    contents = [types.Content(role="user", parts=parts_list)]
    
    # --- NOVA CONFIGURAÇÃO DE GERAÇÃO PARA MP3 ---
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["audio/mp3"] # Pedimos o áudio diretamente em MP3
    )
    speech_config = types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
        )
    )

    audio_data = None
    model_to_use = "Pro"
    
    try:
        # Tenta com o modelo PRO
        print(f"Tentando gerar com o modelo: {model_pro}")
        response = client.models.generate_content(
            model=model_pro,
            contents=contents,
            config=generate_content_config,
            speech_config=speech_config
        )
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        print("Sucesso com o modelo Pro!")
        
    except Exception as e:
        if "resource_exhausted" in str(e).lower() or "quota" in str(e).lower():
            print(f"Cota do Pro esgotada. Tentando com o modelo Flash.")
            model_to_use = "Flash"
            try:
                # Tenta com o modelo FLASH
                print(f"Tentando gerar com o modelo: {model_flash}")
                response = client.models.generate_content(
                    model=model_flash,
                    contents=contents,
                    config=generate_content_config,
                    speech_config=speech_config
                )
                audio_data = response.candidates[0].content.parts[0].inline_data.data
                print("Sucesso com o modelo Flash!")
            except Exception as e_flash:
                return jsonify({"error": f"Ambos os modelos falharam. Erro Flash: {e_flash}"}), 500
        else:
            return jsonify({"error": f"Erro com o modelo Pro: {e}"}), 500

    if not audio_data:
        return jsonify({"error": "Não foi possível gerar o áudio"}), 500

    # Cria a resposta e envia o áudio MP3
    response = make_response(send_file(io.BytesIO(audio_data), mimetype='audio/mp3'))
    response.headers['X-Model-Used'] = model_to_use
    return response
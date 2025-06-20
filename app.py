import os
import io
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app, origins="*", expose_headers=['X-Model-Used'])

@app.route('/')
def home():
    return "Backend do Estúdio Virtual está online. Versão 2.1"

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
    
    # Prepara o conteúdo da requisição
    prompt = f"{style_instructions_text}\n\n{text_to_narrate}" if style_instructions_text else text_to_narrate
    
    # Define os modelos a serem tentados
    model_pro = "gemini-2.5-pro-preview-tts"
    model_flash = "gemini-2.5-flash-preview-tts"

    audio_data = None
    model_to_use = "Pro"
    
    try:
        # Tenta com o modelo PRO
        print(f"Tentando gerar com o modelo: {model_pro}")
        response = client.text_to_speech(
            model_name=model_pro,
            text=prompt,
            voice_name=voice_name
        )
        audio_data = response.audio
        print("Sucesso com o modelo Pro!")
        
    except Exception as e:
        if "resource_exhausted" in str(e).lower() or "quota" in str(e).lower():
            print(f"Cota do Pro esgotada. Tentando com o modelo Flash.")
            model_to_use = "Flash"
            try:
                # Tenta com o modelo FLASH
                print(f"Tentando gerar com o modelo: {model_flash}")
                response = client.text_to_speech(
                    model_name=model_flash,
                    text=prompt,
                    voice_name=voice_name
                )
                audio_data = response.audio
                print("Sucesso com o modelo Flash!")
            except Exception as e_flash:
                error_message = f"Ambos os modelos falharam. Erro Flash: {e_flash}"
                print(error_message)
                return jsonify({"error": error_message}), 500
        else:
            error_message = f"Erro com o modelo Pro: {e}"
            print(error_message)
            return jsonify({"error": error_message}), 500

    if not audio_data:
        return jsonify({"error": "Não foi possível gerar o áudio"}), 500

    # Cria a resposta e envia o áudio MP3
    response = make_response(send_file(io.BytesIO(audio_data), mimetype='audio/mp3'))
    response.headers['X-Model-Used'] = model_to_use
    return response
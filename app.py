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
    return "Backend do Estúdio Virtual está online. Versão 2.2 (Final)"

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
    
    # Prepara o conteúdo da requisição
    prompt = f"{style_instructions_text}\n\n{text_to_narrate}" if style_instructions_text else text_to_narrate
    
    # Define os modelos a serem tentados
    models_to_try = [
        ("Pro", "gemini-2.5-pro-preview-tts"),
        ("Flash", "gemini-2.5-flash-preview-tts")
    ]
    
    audio_data = None
    model_used = "Nenhum"

    for friendly_name, model_name in models_to_try:
        try:
            print(f"Tentando gerar com o modelo: {model_name}")

            # --- CORREÇÃO APLICADA AQUI ---
            # 1. Cria a configuração da fala
            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )

            # 2. Cria a configuração de geração, passando o speech_config DENTRO dela
            final_config = types.GenerateContentConfig(
                response_modalities=["audio/mp3"],
                speech_config=speech_config 
            )

            # 3. Faz a chamada com o objeto de configuração único
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt], # Passando o prompt diretamente
                config=final_config
            )
            
            if response.candidates and response.candidates[0].content.parts:
                audio_data = response.candidates[0].content.parts[0].inline_data.data
                model_used = friendly_name
                print(f"Sucesso com o modelo {friendly_name}!")
                break # Sai do loop se a geração foi bem-sucedida
            
        except Exception as e:
            if "resource_exhausted" in str(e).lower() or "quota" in str(e).lower():
                print(f"Cota do modelo {friendly_name} esgotada. Tentando o próximo.")
                continue # Continua para o próximo modelo na lista
            else:
                print(f"Erro inesperado com o modelo {friendly_name}: {e}")
                return jsonify({"error": f"Erro na API do Gemini: {e}"}), 500
    
    if not audio_data:
        return jsonify({"error": "Não foi possível gerar o áudio com nenhum dos modelos disponíveis."}), 500

    # Cria a resposta e envia o áudio MP3
    response_http = make_response(send_file(io.BytesIO(audio_data), mimetype='audio/mp3'))
    response_http.headers['X-Model-Used'] = model_used
    return response_http
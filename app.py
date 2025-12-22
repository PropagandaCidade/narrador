# app.py - VERSÃO 20.0 - ARQUITETURA FINAL
# DESCRIÇÃO: Esta versão implementa a arquitetura de "Fonte Única da Verdade".
# A dependência do 'text_utils.py' foi COMPLETAMENTE REMOVIDA.
# O script agora confia 100% no texto já normalizado que recebe do TextNormalizer.php
# e atua apenas como um conector para a API de TTS.

import os
import io
import logging

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

from pydub import AudioSegment

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização do Flask App
app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

@app.route('/')
def home():
    # Mensagem de status clara que reflete a nova arquitetura
    return "Serviço de Narração v20.0 (Arquitetura Simplificada - Fonte da Verdade PHP) está online."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    logger.info("Recebendo solicitação para /api/generate-audio")
    
    # 1. Validação da API Key e dos dados de entrada
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        error_msg = "ERRO CRÍTICO: GEMINI_API_KEY não encontrada no ambiente."
        logger.error(error_msg)
        return jsonify({"error": "Configuração do servidor incompleta."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida (corpo JSON ausente)."}), 400

    # O texto recebido já está 100% normalizado pelo PHP
    final_text_from_php = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash') # 'flash' como padrão

    if not final_text_from_php or not voice_name:
        return jsonify({"error": "Os campos 'text' e 'voice' são obrigatórios."}), 400

    try:
        # 2. Limite de segurança de caracteres (boa prática)
        INPUT_CHAR_LIMIT = 4950 # Limite seguro para a API
        if len(final_text_from_php) > INPUT_CHAR_LIMIT:
            logger.warning(f"Texto ({len(final_text_from_php)} chars) excedeu o limite. Truncando...")
            final_text_from_php = final_text_from_php[:INPUT_CHAR_LIMIT]

        # --- A MUDANÇA ARQUITETURAL CRÍTICA ---
        # Nenhuma chamada para text_utils.py. Nenhuma normalização.
        # O texto do PHP é a verdade absoluta.
        logger.info(f"Texto final (confiado do PHP) para TTS: '{final_text_from_php[:150]}...'")
        
        # 3. Mapeamento do modelo e configuração da API
        model_to_use_fullname = "gemini-1.5-flash-tts-001" if model_nickname != 'pro' else "gemini-1.5-pro-tts-001"
        logger.info(f"Usando modelo TTS: {model_to_use_fullname}")
        
        client = genai.Client(api_key=api_key)
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        # 4. Geração do áudio via streaming
        audio_data_chunks = []
        for chunk in client.models.generate_content_stream(
            model=model_to_use_fullname,
            contents=final_text_from_php, # Usando o texto final diretamente
            config=generate_content_config
        ):
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_data_chunks:
             logger.error("A API do Google respondeu, mas não retornou dados de áudio.")
             return jsonify({"error": "Falha na geração de áudio pela API externa."}), 500

        # 5. Processamento e conversão para MP3
        full_audio_data_raw = b''.join(audio_data_chunks)
        logger.info("Áudio bruto recebido. Convertendo para MP3 Mono...")
        
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(full_audio_data_raw),
            sample_width=2,
            frame_rate=24000,
            channels=1
        )
        
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
        mp3_data = mp3_buffer.getvalue()
        
        logger.info(f"Conversão para MP3 concluída. Tamanho: {len(mp3_data) / 1024:.2f} KB")

        # 6. Envio da resposta de áudio
        http_response = make_response(send_file(
            io.BytesIO(mp3_data),
            mimetype='audio/mpeg',
            as_attachment=False
        ))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info("Sucesso: Áudio MP3 gerado e enviado ao cliente.")
        return http_response

    except Exception as e:
        error_message = f"Erro inesperado no serviço Python: {e}"
        logger.error(f"ERRO CRÍTICO: {error_message}", exc_info=True)
        return jsonify({"error": error_message, "user_message": "Ocorreu uma falha interna no serviço de geração de áudio."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080)) # Porta padrão para muitos serviços de nuvem
    app.run(host='0.0.0.0', port=port)
# app.py - VERSÃO 23.6 - DASHBOARD MODE (SYNC WITH PHP CONTEXT GUARD)
# DESCRIÇÃO: Motor de Geração ajustado para limpar as tags <context_guard> do PHP
#            e usar o texto normalizado como conteúdo primário.

import os
import base64
import struct
import requests
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Importa bibliotecas
try:
    import google.generativeai as genai
    from google.generativeai import types
except ImportError:
    raise ImportError("Instale a biblioteca google-generativeai: pip install google-generativeai")

from pydub import AudioSegment
import io
import logging
import time
import random

# Configuração
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
CORS(app, expose_headers=['X-Model-Used'])

api_key = os.environ.get("GEMINI_API_KEY")

class AudioRequest(BaseModel):
    text: str
    voice: str = "Puck"
    speed: float = 1.0
    instrucao: str = "" 
    temp: float = 0.7
    categoria: str = "Geral" 

@app.get("/")
def health_check():
    return {"status": "online", "engine": "Voice Hub Python V23.6 (PHP Context Sync)"}

def add_wav_header(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    data_size = len(pcm_data)
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + data_size, b'WAVE', b'fmt ', 16, 1, channels, sample_rate, byte_rate, block_align, bits_per_sample, b'data', data_size)
    return header + pcm_data

def get_model_fullname(nickname: str) -> str:
    if nickname in ['pro', 'chirp']:
        return "gemini-2.5-pro-preview-tts"
    return "gemini-2.5-flash-preview-tts"

@app.post("/generate-audio")
async def generate_audio(req: AudioRequest):
    if not api_key:
        logger.error("Chave API ausente.")
        return jsonify({"error": "Configuração do servidor incompleta."}), 500

    data = request.get_json()
    text = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')
    
    try:
        temperature = float(data.get('temperature', 0.85))
    except:
        temperature = 0.85

    if not text or not voice_name:
        return jsonify({"error": "Texto e voz são obrigatórios."}), 400

    try:
        # 1. LIMPEZA DO TEXTO RECEBIDO DO PHP: REMOVE A TAG <context_guard>
        # Isso garante que o Google só receba o texto final limpo.
        text_for_ia = text.replace("<context_guard>", "").replace("</context_guard>", "").strip()
        
        # 2. Mapeamento de Modelos
        model_fullname = get_model_fullname(model_nickname)
            
        logger.info(f"Usando modelo: {model_fullname} | Temp: {temperature}")
        
        client = genai.Client(api_key=api_key)

        # 3. CONFIGURAÇÃO - SYSTEM INSTRUCTION SIMPLIFICADA
        system_instruction_final = (
            "Você é um locutor profissional. Leia o texto EXATAMENTE como ele está escrito. Não faça correções gramaticais ou de pontuação, apenas a locução."
        )
        
        generate_config = types.GenerateContentConfig(
            system_instruction=system_instruction_final,
            temperature=temperature,
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
        )
        
        # 4. Geração (Usando chamada não-stream para estabilidade, como no teste)
        response = client.models.generate_content(
            model=model_fullname,
            contents=text_for_ia,
            config=generate_config
        )

        if not response.candidates or not response.candidates[0].content.parts:
             raise Exception("API Google falhou: Resposta sem áudio.")

        inline_data = response.candidates[0].content.parts[0].inlineData.data
        pcm_bytes = base64.b64decode(inline_data)
        
        # 5. Conversão para MP3
        wav_bytes = add_wav_header(pcm_bytes)
        mp3_data = base64.b64encode(wav_bytes).decode('utf-8')
        
        # 6. Resposta
        http_response = make_response(send_file(
            io.BytesIO(base64.b64decode(mp3_data)),
            mimetype='audio/mpeg',
            as_attachment=False
        ))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso ({model_nickname}).")
        return http_response

    except google_exceptions.ServerError as e:
        logger.error(f"ERRO 500 Google API (Tentativas esgotadas ou falha interna): {e}", exc_info=True)
        return jsonify({"error": "Serviço de Voz do Google com erro interno. Tente novamente mais tarde."}), 500
    except Exception as e:
        logger.error(f"ERRO CRÍTICO no Servidor Python: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
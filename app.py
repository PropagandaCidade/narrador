# app.py - VERSÃO 23.3 - STUDIO & DASHBOARD SYNC (SIMPLIFIED PAYLOAD)
# DESCRIÇÃO: Motor de Geração com payload limpo, confiando 100% na normalização do PHP (ContextGuard).

import os
import base64
import struct
import requests
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    import google.generativeai as genai
    from google.generativeai import types
    from google.api_core import exceptions as google_exceptions
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
def home():
    return {"status": "online", "engine": "Voice Hub Python V23.3 (Simplified Payload)"}

def add_wav_header(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    data_size = len(pcm_data)
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + data_size, b'WAVE', b'fmt ', 16, 1, channels, sample_rate, byte_rate, block_align, bits_per_sample, b'data', data_size)
    return header + pcm_data

@app.post("/generate-audio")
async def generate_audio(req: AudioRequest):
    if not api_key:
        logger.error("Chave API ausente.")
        return jsonify({"error": "Configuração do servidor incompleta."}), 500

    data = request.get_json()
    text = data.get('text')
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')
    
    # Captura a instrução (que virá do Studio Hub, mas será ignorada se for muito longa)
    custom_prompt = data.get('custom_prompt', '').strip() 

    try:
        temperature = float(data.get('temperature', 0.85))
    except (ValueError, TypeError):
        temperature = 0.85

    if not text or not voice_name:
        return jsonify({"error": "Texto ou voz são obrigatórios."}), 400

    try:
        # 1. LIMPEZA DO TEXTO RECEBIDO DO PHP
        # Removemos o <context_guard> antes de enviar para o Google, pois o Google pode não gostar.
        # O texto já está normalizado pelo PHP, então só precisamos limpá-lo de tags.
        text_for_ia = text.replace("<context_guard>", "").replace("</context_guard>", "").strip()
        
        # 2. DEFINIÇÃO DO MODELO
        model_fullname = get_model_fullname(model_nickname)
            
        logger.info(f"Usando modelo: {model_to_use_fullname} | Temperatura: {temperature}")
        
        client = genai.Client(api_key=api_key)

        # 3. CONFIGURAÇÃO - INSTRUÇÃO SIMPLES PARA MINIMIZAR ERRO 500
        # A instrução deve ser concisa para evitar que a IA "fale o prompt"
        system_instruction_final = (
            "Leia o texto fornecido de forma clara e profissional. Mantenha a pontuação e o ritmo."
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
        
        # 4. GERAÇÃO VIA STREAMING
        audio_data_chunks = []
        
        # O 'contents' recebe o texto LIMPO (sem as tags do PHP)
        for chunk in client.models.generate_content_stream(
            model=model_fullname,
            contents=text_for_ia, # Usa o texto puro
            config=generate_content_config
        ):
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)

        if not audio_data_chunks:
             raise Exception("API do Google não retornou dados de áudio.")

        # 5. Processamento e conversão para MP3 (Pydub)
        full_audio_data_raw = b''.join(audio_data_chunks)
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(full_audio_data_raw),
            sample_width=2,
            frame_rate=24000,
            channels=1
        )
        
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="64k")
        mp3_data = mp3_buffer.getvalue()
        
        # 6. Resposta
        http_response = make_response(send_file(
            io.BytesIO(mp3_data),
            mimetype='audio/mpeg',
            as_attachment=False
        ))
        http_response.headers['X-Model-Used'] = model_nickname
        
        logger.info(f"Sucesso no Servidor 01: Áudio gerado ({model_nickname}).")
        return http_response

    except Exception as e:
        logger.error(f"ERRO CRÍTICO NO SERVIDOR 01: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
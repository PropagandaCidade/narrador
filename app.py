# app.py - VERSÃO 23.7 - FINAL STABLE PAYLOAD & CLEANUP FOR DASHBOARD INPUT
# DESCRIÇÃO: Motor de Geração com limpeza de tags e foco em estabilidade para o Dashboard.

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
    return {"status": "online", "engine": "Voice Hub Python V23.7 (Stability Mode)"}

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
        # 1. LIMPEZA DO TEXTO RECEBIDO DO PHP
        # Removemos a tag <context_guard> que vem do router.php
        text_for_ia = text.replace("<context_guard>", "").replace("</context_guard>", "").strip()
        
        # 2. Mapeamento e Configuração
        model_fullname = get_model_fullname(model_nickname)
        
        logger.info(f"Usando modelo: {model_fullname} | Temp: {temperature}")
        
        client = genai.Client(api_key=api_key)

        # 3. SYSTEM INSTRUCTION MINIMALISTA (Menos chance de conflito com o texto)
        system_instruction_final = (
            "Gere o áudio com tom neutro e profissional. Leia o texto EXATAMENTE como está escrito. Não faça correções."
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
        
        # 4. Geração via STREAMING (Voltamos para stream por ser mais rápido, confiando no retry)
        audio_data_chunks = []
        
        # Tentativa com Loop de Retry (para o erro 500)
        for attempt in range(3):
            try:
                response = client.models.generate_content_stream(
                    model=model_fullname,
                    contents=text_for_ia,
                    config=generate_config
                )
                
                # Processa chunks da stream
                for chunk in response:
                    if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                        audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)
                
                if audio_data_chunks:
                    break # Sucesso, sai do loop de tentativas

            except google_exceptions.InternalServerError as e:
                logger.error(f"Tentativa {attempt + 1} falhou (Google 500): {e}")
                if attempt < 2:
                    time.sleep(random.uniform(2, 4))
                    continue
                raise RuntimeError(f"API Google falhou após 3 tentativas com 500 Internal.")
            except Exception as e:
                logger.error(f"Erro durante a stream: {e}", exc_info=True)
                raise RuntimeError(f"Erro na stream: {e}")

        if not audio_data_chunks:
             raise ValueError("API do Google não retornou dados de áudio.")

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
        
        logger.info(f"Sucesso ({model_nickname}).")
        return http_response

    except Exception as e:
        logger.error(f"ERRO CRÍTICO NO SERVIDOR 01: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
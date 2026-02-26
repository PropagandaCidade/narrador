# app.py - VERSÃO 23.4 - FINAL MINIMALIST PAYLOAD
# DESCRIÇÃO: Motor de Geração com payload reduzido para máxima estabilidade com a Skill PHP.

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

# Inicialização
app = FastAPI()
CORS(app, expose_headers=['X-Model-Used'])
api_key = os.environ.get("GEMINI_API_KEY")

class AudioRequest(BaseModel):
    text: str
    voice: str = "Puck"
    speed: float = 1.0
    instrucao: str = "" # Parâmetro mantido, mas ignorado no payload final
    temp: float = 0.7
    categoria: str = "Geral" 

@app.get("/")
def home():
    return {"status": "online", "engine": "Voice Hub Python V23.4 (Minimalist Payload)"}

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
        # 1. TEXTO ENVIADO: APENAS O TEXTO LIMPO DO PHP (com <context_guard>)
        text_for_ia = text.strip()
        
        # 2. Mapeamento de Modelos
        model_to_use_fullname = get_model_fullname(model_nickname)
            
        logger.info(f"Usando modelo: {model_to_use_fullname} | Temp: {temperature}")
        
        client = genai.Client(api_key=api_key)

        # 3. CONFIGURAÇÃO - SYSTEM INSTRUCTION MINIMALISTA
        # Esta instrução é mais genérica e menos propensa a ser sinalizada como erro de prompt
        system_instruction_minimal = (
            "Gere o áudio com tom neutro e profissional. Leia o texto palavra por palavra, respeitando a pontuação fornecida."
        )
        
        generate_config = types.GenerateContentConfig(
            system_instruction=system_instruction_minimal, # Instrução simples
            temperature=temperature,
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        # 4. Geração via Streaming
        audio_data_chunks = []
        response = None 
        
        for attempt in range(3):
            try:
                # O 'contents' recebe o texto completo do PHP (incluindo a tag <context_guard> se for do Studio)
                response = client.models.generate_content_stream(
                    model=model_to_use_fullname,
                    contents=text_for_ia,
                    config=generate_config
                )
                
                # Processamento de Streaming (compatível com o código anterior)
                for chunk in response:
                    if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                        audio_data_chunks.append(chunk.candidates[0].content.parts[0].inline_data.data)
                
                if audio_data_chunks:
                    break # Saímos do loop se conseguirmos dados
            
            except google_exceptions.InternalServerError as e:
                logger.error(f"Tentativa {attempt + 1} falhou (Google 500): {e}")
                if attempt < 2:
                    time.sleep(random.uniform(1, 3))
                    continue
                raise RuntimeError(f"Google API Falhou após 3 tentativas: {e}")
            except Exception as e:
                logger.error(f"Erro durante a iteração da stream: {e}", exc_info=True)
                raise RuntimeError(f"Erro interno na stream: {e}")

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
        logger.error(f"ERRO CRÍTICO: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
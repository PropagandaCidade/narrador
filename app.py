# app.py - VERSÃO 23.2 - CONTEXT GUARD SYNC & SYSTEM INSTRUCTION PRIORITY
# DESCRIÇÃO: Motor de Geração de Áudio com roteamento e normalização via Skill PHP.
# Otimizado para evitar erros 500 e manter consistência.

import os
import base64
import struct
import requests
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Importa a biblioteca do Google GenAI
# Se esta biblioteca não estiver instalada, use: pip install google-generativeai
try:
    import google.generativeai as genai
    from google.generativeai import types
    from google.api_core import exceptions as google_exceptions
except ImportError:
    raise ImportError("Por favor, instale a biblioteca google-generativeai: pip install google-generativeai")

from pydub import AudioSegment
import io
import logging
import time
import random

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização do Flask App
app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used'])

# CHAVE DA API (DEVE ESTAR DEFINIDA NO AMBIENTE DO SERVIDOR)
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    logger.error("ERRO: GEMINI_API_KEY não encontrada no ambiente.")
    # Para desenvolvimento local, pode ser útil ter uma chave dummy, mas em produção é essencial.

# Schemas de Requisição com Pydantic
class AudioRequest(BaseModel):
    text: str
    voice: str = "Puck"
    speed: float = 1.0
    instrucao: str = "" 
    temp: float = 0.7
    categoria: str = "Geral" 

@app.get("/")
def health_check():
    return {"status": "online", "engine": "Voice Hub Python V23.2 (Context Guard Synced)"}

# --- FUNÇÕES AUXILIARES ---

def add_wav_header(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """Adiciona cabeçalho WAV aos dados brutos PCM."""
    data_size = len(pcm_data)
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + data_size, b'WAVE', b'fmt ', 16, 1, channels, sample_rate, byte_rate, block_align, bits_per_sample, b'data', data_size)
    return header + pcm_data

def get_model_fullname(nickname: str) -> str:
    """Mapeia apelidos de modelo para nomes completos da API."""
    if nickname in ['pro', 'chirp']:
        return "gemini-2.5-pro-preview-tts"
    return "gemini-2.5-flash-preview-tts"

# --- ENDPOINT DE GERAÇÃO ---
@app.post("/generate-audio")
async def generate_audio(req: AudioRequest):
    if not api_key:
        logger.error("Chave API ausente.")
        return jsonify({"error": "Configuração do servidor incompleta."}), 500

    if not req.text or not req.voice:
        return jsonify({"error": "Texto ou voz obrigatórios."}), 400

    try:
        # 1. PREPARAÇÃO DOS PARÂMETROS
        voice_name_formatted = req.voice.strip().capitalize()
        model_fullname = get_model_fullname(req.model_to_use)
        
        # Consolida instruções: Prompt do PHP + Instrução do Usuário
        # O sistema priorizará a instrução do SYSTEM_INSTRUCTION da API do Google
        final_content = req.text.strip()
        
        # Adiciona instrução do usuário se existir
        if req.instrucao:
            final_content = f"Contexto: {req.instrucao}\n\nTexto:\n{final_content}"

        # Define a temperatura (criatividade)
        temperature = max(0.1, min(1.5, req.temp)) # Garante que a temperatura esteja dentro de limites razoáveis

        # 2. CONFIGURAÇÃO DA SOLICITAÇÃO AO GEMINI
        # Usamos a System Instruction para MANDAR a IA respeitar o que o PHP normalizou.
        system_instruction_gemini = (
            "Você é um locutor profissional brasileiro. Leia o texto EXATAMENTE como está escrito. "
            "Mantenha a pontuação, números e palavras em extenso que já foram normalizados. "
            "Não altere o texto original fornecido na entrada. Sua tarefa é apenas a locução."
        )
        
        generate_config = types.GenerateContentConfig(
            system_instruction=system_instruction_gemini,
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

        # 3. CHAMADA À API DO GOOGLE GEMINI (COM RETRIES)
        # O loop de retry já está implementado na biblioteca google-generativeai
        audio_data_chunks = []
        response = None # Inicializa a variável response
        
        logger.info(f"Chamando Gemini: Modelo={model_to_use}, Voz={voice_name}, Temp={temperature}")
        
        # Tenta chamar a API uma vez, confiando que a biblioteca gerenciará retries
        try:
            response = client.models.generate_content(
                model=model_to_use,
                contents=final_content,
                generation_config=generate_content_config
            )
            
            # Se a chamada direta não foi stream, processamos o resultado
            if hasattr(response, 'text'):
                 audio_data_chunks.append(response.text) # Ou onde o áudio é retornado
            elif hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                             if 'inlineData' in part and 'data' in part.inlineData:
                                audio_data_chunks.append(part.inlineData.data)

        except google_exceptions.GoogleAPIError as e:
            logger.error(f"Erro da API Google: {e}")
            raise RuntimeError(f"Erro na API Google: {e}") from e
        except Exception as e:
            logger.error(f"Erro inesperado na chamada da API: {e}")
            raise RuntimeError(f"Erro genérico na chamada da API: {e}")

        if not audio_data_chunks:
            raise ValueError("A API do Google não retornou dados de áudio.")

        # 4. PROCESSAMENTO E CONVERSÃO PARA MP3 (PYDUB)
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
        
        # 5. RESPOSTA FINAL
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
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    # O servidor deve ser iniciado de forma diferente em produção (ex: Gunicorn)
    # Mas para desenvolvimento local, isso funciona.
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
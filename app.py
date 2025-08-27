# app.py - VERSÃO FINAL COM ROTEAMENTO INTELIGENTE, ROTAÇÃO DE CHAVES E RECUO EXPONENCIAL
import os
import io
import mimetypes
import struct
import logging
import random # Adicionado para rotação de chaves
import time   # Adicionado para o recuo exponencial

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS

# Importações da biblioteca do Google
import google.generativeai as genai
from google.generativeai import types
from google.api_core import exceptions # Importante para capturar o erro específico de cota

# --- Configuração de logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Expõe o cabeçalho personalizado 'X-Model-Used' para o frontend
CORS(app, expose_headers=['X-Model-Used'])

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """
    Gera um cabeçalho WAV para os dados de áudio recebidos.
    """
    logger.info(f"Convertendo dados de áudio de {mime_type} para WAV...")
    
    bits_per_sample = 16
    sample_rate = 24000 
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels,
        sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size
    )
    logger.info("Conversão para WAV concluída.")
    return header + audio_data

@app.route('/')
def home():
    """Rota para verificar se o serviço está online."""
    logger.info("Endpoint '/' acessado.")
    # Mensagem atualizada para refletir as novas capacidades
    return "Serviço de Narração no Railway está online e estável! (Usando Roteamento, Rotação de Chaves e Recuo Exponencial)"

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    """Endpoint principal que gera o áudio."""
    logger.info("Recebendo solicitação para /api/generate-audio")
    
    # --- [NOVO] PARTE 1: ROTAÇÃO DE API KEYS ---
    api_keys_str = os.environ.get("GEMINI_API_KEYS")
    if not api_keys_str:
        error_msg = "ERRO CRÍTICO: Variável de ambiente GEMINI_API_KEYS não encontrada."
        logger.error(error_msg)
        return jsonify({"error": "Configuração do servidor incompleta."}), 500
    
    # Transforma a string de chaves em uma lista e escolhe uma aleatoriamente
    api_keys = [key.strip() for key in api_keys_str.split(',') if key.strip()]
    if not api_keys:
        return jsonify({"error": "Nenhuma chave de API válida encontrada na configuração."}), 500
        
    api_key = random.choice(api_keys)
    logger.info(f"Usando uma chave de API selecionada aleatoriamente de um pool de {len(api_keys)} chaves.")
    # --- FIM DA PARTE 1 ---

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida, corpo JSON ausente."}), 400

    text_to_process = data.get('text') 
    voice_name = data.get('voice')
    model_nickname = data.get('model_to_use', 'flash')

    if not text_to_process or not voice_name:
        return jsonify({"error": "Os campos de texto e voz são obrigatórios."}), 400

    # --- [NOVO] PARTE 2: LÓGICA DE RECUO EXPONENCIAL ---
    max_retries = 4  # Número máximo de tentativas
    base_delay = 2   # Atraso inicial em segundos

    for attempt in range(max_retries):
        try:
            # --- LÓGICA DE SELEÇÃO DE MODELO (MANTIDA EXATAMENTE COMO A SUA) ---
            if model_nickname == 'pro':
                model_to_use_fullname = "gemini-2.5-pro-preview-tts"
            else:
                model_to_use_fullname = "gemini-2.5-flash-preview-tts"
            
            logger.info(f"Tentativa {attempt + 1}/{max_retries}. Frontend solicitou '{model_nickname}'. Usando: {model_to_use_fullname}")
            
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
            
            audio_data_chunks = []
            for chunk in client.models.generate_content_stream(
                model=model_to_use_fullname,
                contents=text_to_process,
                config=generate_content_config
            ):
                if (chunk.candidates and chunk.candidates[0].content and 
                    chunk.candidates[0].content.parts and
                    chunk.candidates[0].content.parts[0].inline_data and 
                    chunk.candidates[0].content.parts[0].inline_data.data):
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    audio_data_chunks.append(inline_data.data)

            if not audio_data_chunks:
                 return jsonify({"error": "A API respondeu, mas não retornou dados de áudio."}), 500

            full_audio_data = b''.join(audio_data_chunks)
            mime_type = inline_data.mime_type if 'inline_data' in locals() else "audio/unknown"
            wav_data = convert_to_wav(full_audio_data, mime_type)
            
            http_response = make_response(send_file(
                io.BytesIO(wav_data), mimetype='audio/wav', as_attachment=False
            ))
            
            http_response.headers['X-Model-Used'] = model_nickname
            
            logger.info(f"Sucesso: Áudio WAV gerado com '{model_nickname}' e enviado ao cliente.")
            return http_response # << IMPORTANTE: Retorna a resposta e sai do loop em caso de sucesso

        except exceptions.ResourceExhausted as e:
            logger.warning(f"Erro de limite de taxa (429) na tentativa {attempt + 1}. Mensagem: {e}")
            if attempt == max_retries - 1:
                logger.error("Número máximo de tentativas atingido. Desistindo.")
                # Retorna o erro original da API para o cliente, que é mais informativo
                error_message = f"Erro do gerador de áudio: {e}"
                return jsonify({"error": error_message}), 429
            
            # Calcula o tempo de espera com um fator aleatório (jitter)
            wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
            logger.info(f"Aguardando {wait_time:.2f} segundos antes de tentar novamente...")
            time.sleep(wait_time)
        
        except Exception as e:
            # Captura outros erros inesperados para não tentar novamente
            error_message = f"Erro inesperado ao contatar a API do Google GenAI: {e}"
            logger.error(f"ERRO CRÍTICO NA API: {error_message}", exc_info=True)
            return jsonify({"error": error_message}), 500
    # --- FIM DA PARTE 2 ---

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
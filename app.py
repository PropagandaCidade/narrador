import os
import io
import logging
import re
import base64
import httpx
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from pydub import AudioSegment, effects

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HiveWorker")

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used', 'X-Prompt-Tokens', 'X-Output-Tokens'])

# Regra de Pronúncia Centralizada
PRONUNCIATION_RULES = "Sempre que encontrar a marca 'IDE', pronuncie exatamente como 'Ídê' (I aberto, Dê fechado). Nunca pronuncie como 'ideia'."

def clean_skill_tags(text):
    return re.sub(r'</?context_guard>', '', text).strip() if text else ""

@app.route('/')
def home():
    return f"Serviço v29.4 (Corrigido) - Ready."

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados inválidos."}), 400

        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        text_to_narrate = clean_skill_tags(data.get('text', ''))
        voice_name = str(data.get('voice', 'Kore')).capitalize()
        model_nickname = str(data.get('model_to_use', 'flash')).lower()
        custom_prompt = data.get('custom_prompt', '').strip()
        use_phonetic = data.get('phonetic', True)
        
        if not text_to_narrate:
            return jsonify({"error": "Texto obrigatório."}), 400

        # Seleção de Modelo
        if "3.1" in model_nickname:
            model_fullname = "gemini-3.1-flash-tts-preview"
        elif "pro" in model_nickname:
            model_fullname = "gemini-2.5-pro-preview-tts"
        else:
            model_fullname = "gemini-2.5-flash-preview-tts"

        # Montagem do System Instruction (Onde as regras de leitura devem ficar)
        system_instructions = []
        if use_phonetic:
            system_instructions.append(PRONUNCIATION_RULES)
        if custom_prompt:
            system_instructions.append(custom_prompt)
        
        # Payload Estrito conforme documentação Google v1beta
        payload = {
            "contents": [{"parts": [{"text": text_to_narrate}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voice_name": voice_name}}
                }
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}
            ]
        }

        # Adiciona systemInstruction apenas se necessário
        if system_instructions:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_instructions)}]}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_fullname}:generateContent?key={api_key}"

        with httpx.Client(timeout=120.0) as client:
            res = client.post(url, json=payload)
            res_json = res.json()
            
            if res.status_code != 200:
                logger.error(f"Erro API: {res.text}")
                return jsonify({"error": "Falha na geração", "details": res.text}), res.status_code

            # Extração segura
            candidate = res_json.get('candidates', [{}])[0]
            parts = candidate.get('content', {}).get('parts', [])
            if not parts or 'inlineData' not in parts[0]:
                return jsonify({"error": "Áudio não retornado pela API"}), 500
            
            response_audio_bytes = base64.b64decode(parts[0]['inlineData']['data'])

        # Processamento de Áudio
        audio_segment = AudioSegment.from_raw(
            io.BytesIO(response_audio_bytes), sample_width=2, frame_rate=24000, channels=1
        )
        audio_segment = effects.normalize(audio_segment, headroom=0.45).set_frame_rate(44100)
        
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3", bitrate="192k", parameters=["-ac", "1", "-ar", "44100"])
        mp3_buffer.seek(0)
        
        response = make_response(send_file(mp3_buffer, mimetype='audio/mpeg'))
        response.headers['X-Model-Used'] = model_fullname
        return response

    except Exception as e:
        logger.error(f"Erro Crítico: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
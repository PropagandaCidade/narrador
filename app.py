import os
import io
import logging
import re
import base64
import httpx
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from pydub import AudioSegment, effects

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HiveWorker")

app = Flask(__name__)
CORS(app, expose_headers=['X-Model-Used', 'X-Prompt-Tokens', 'X-Output-Tokens'])

PRONUNCIATION_RULES = "Sempre pronuncie a marca 'IDE' como 'Ídê' (I aberto, Dê fechado). Nunca diga 'ideia'."

def clean_skill_tags(text):
    return re.sub(r'</?context_guard>', '', text).strip() if text else ""

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_endpoint():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        text_to_narrate = clean_skill_tags(data.get('text', ''))
        voice_name = str(data.get('voice', 'Kore')).capitalize()
        model_nickname = str(data.get('model_to_use', 'flash')).lower()
        custom_prompt = data.get('custom_prompt', '').strip()
        
        # Seleção de modelo
        model_fullname = "gemini-2.5-flash-preview-tts"
        if "3.1" in model_nickname: model_fullname = "gemini-3.1-flash-tts-preview"
        elif "pro" in model_nickname: model_fullname = "gemini-2.5-pro-preview-tts"

        # Payload estrito (Google exige esta hierarquia exata)
        payload = {
            "contents": [{"parts": [{"text": text_to_narrate}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voice_name": voice_name}}
                }
            }
        }
        
        # Adiciona instrução de sistema se houver
        sys_instr = f"{PRONUNCIATION_RULES}\n{custom_prompt}".strip()
        if sys_instr:
            payload["systemInstruction"] = {"parts": [{"text": sys_instr}]}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_fullname}:generateContent?key={api_key}"

        with httpx.Client(timeout=120.0) as client:
            res = client.post(url, json=payload)
            if res.status_code != 200:
                logger.error(f"Erro API: {res.text}")
                return jsonify({"error": "Erro na API do Google", "details": res.text}), res.status_code
            
            res_json = res.json()
            # Extração segura
            candidate = res_json.get('candidates', [{}])[0]
            parts = candidate.get('content', {}).get('parts', [])
            if not parts or 'inlineData' not in parts[0]:
                return jsonify({"error": "Nenhum áudio gerado."}), 500
            
            response_audio_bytes = base64.b64decode(parts[0]['inlineData']['data'])

        # Processamento
        seg = AudioSegment.from_raw(io.BytesIO(response_audio_bytes), sample_width=2, frame_rate=24000, channels=1)
        seg = effects.normalize(seg).set_frame_rate(44100)
        
        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="192k")
        out.seek(0)
        
        return send_file(out, mimetype='audio/mpeg')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
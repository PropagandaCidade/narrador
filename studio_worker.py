import os, io, json, base64, httpx, logging
from flask import Flask, request, jsonify, send_file, make_response
from pydub import AudioSegment, effects

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StudioWorker")
app = Flask(__name__)

# Nota: A lógica do apply_advanced_studio_fx permanece a mesma que você já tinha

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio_studio():
    try:
        data = request.get_json()
        api_key = data.get("GEMINI_API_KEY")
        text = data.get('text', '')
        voice_name = str(data.get('voice', 'Kore')).capitalize()
        
        # Payload seguindo o mesmo padrão validado
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "systemInstruction": {"parts": [{"text": "Sempre pronuncie 'IDE' como 'Ídê'."}]},
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voice_name": voice_name}}
                }
            }
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
        
        with httpx.Client(timeout=150.0) as client:
            res = client.post(url, json=payload)
            if res.status_code != 200:
                return jsonify({"error": res.text}), res.status_code
            
            res_json = res.json()
            audio_data = res_json['candidates'][0]['content']['parts'][0]['inlineData']['data']
            response_audio_bytes = base64.b64decode(audio_data)

        seg = AudioSegment.from_raw(io.BytesIO(response_audio_bytes), sample_width=2, frame_rate=24000, channels=1)
        # Aplique seu apply_advanced_studio_fx aqui
        
        out = io.BytesIO()
        seg.export(out, format="mp3", bitrate="128k")
        out.seek(0)
        return send_file(out, mimetype='audio/mpeg')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
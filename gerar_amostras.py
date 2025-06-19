# gerar_amostras.py
import os
from google import genai
from google.genai import types

# Lista de todas as vozes disponíveis
VOZES = ["Aoede", "Calypso", "Euterpe", "Dione", "Iapetus", "Hyperion"]
TEXTO_AMOSTRA = "Olá, esta é uma demonstração da minha voz."

def generate_sample(voice_name: str):
    """Gera um arquivo de áudio para uma voz específica."""
    print(f"Gerando amostra para a voz: {voice_name}...")
    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        model = "gemini-2.5-flash-preview-tts"
        
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=TEXTO_AMOSTRA)])]
        
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        )

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        if response.candidates[0].content.parts[0].inline_data.data:
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            # Salva o arquivo como WAV (formato mais universal)
            file_name = f"{voice_name}.wav"
            with open(file_name, "wb") as f:
                f.write(audio_data)
            print(f"-> Salvo com sucesso em: {file_name}")
        else:
            print(f"-> Falha ao gerar áudio para {voice_name}")

    except Exception as e:
        print(f"ERRO ao gerar para {voice_name}: {e}")

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERRO: Por favor, configure a variável de ambiente GEMINI_API_KEY antes de rodar o script.")
    else:
        for voz in VOZES:
            generate_sample(voz)
        print("\nProcesso concluído!")
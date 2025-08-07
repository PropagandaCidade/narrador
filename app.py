# app.py - VERSÃO DE DEPURAÇÃO MÁXIMA PARA CORS
import os
from flask import Flask, jsonify, request
from flask_cors import CORS

# Log para provar que este arquivo exato está sendo executado
print("--- [DEBUG CORS v3] MÓDULO CARREGADO ---")

app = Flask(__name__)

# --- CONFIGURAÇÃO DE CORS MAIS SIMPLES POSSÍVEL ---
# Aplica a permissão "*" para TODAS as rotas e TODOS os métodos.
# Se isto não funcionar, o problema é 100% da plataforma Railway.
CORS(app)
print("--- [DEBUG CORS v3] CORS INICIALIZADO PARA TODAS AS ROTAS ---")

@app.route('/')
def home():
    """Rota para verificar se o serviço está online."""
    print("--- [DEBUG CORS v3] Rota '/' foi acessada ---")
    return "Serviço de Narração em modo de depuração de CORS está online!"

@app.route('/api/generate-audio', methods=['POST', 'OPTIONS'])
def generate_audio_endpoint():
    """
    Endpoint de depuração. Ignora a lógica do Gemini e apenas responde
    com sucesso para testar a conexão CORS.
    """
    # Log para provar que a requisição chegou aqui
    print(f"--- [DEBUG CORS v3] Rota /api/generate-audio acessada com método: {request.method} ---")

    # O navegador envia uma requisição 'OPTIONS' primeiro (preflight).
    # O Flask-CORS deveria lidar com isso, mas estamos sendo explícitos.
    if request.method == 'OPTIONS':
        return '', 204 # Resposta vazia e bem-sucedida para o preflight

    # Se a requisição for 'POST', retorna uma mensagem de sucesso em JSON.
    return jsonify({
        "success": True,
        "message": "Conexão CORS bem-sucedida! O servidor de depuração respondeu.",
        "received_data": request.get_json() # Devolve os dados que recebeu
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
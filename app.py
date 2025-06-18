import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (para desenvolvimento local)
load_dotenv()

app = Flask(__name__)

# --- Configuração das Chaves de API ---
# Pega as chaves das variáveis de ambiente
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

# --- Rota Principal da API (MODO DE DEBUG) ---
# Esta rota não gera áudio. Ela apenas inspeciona e reporta os cabeçalhos recebidos.
@app.route('/generate', methods=['POST'])
def generate_audio_debug_endpoint():
    # Pega todos os cabeçalhos da requisição e os transforma em um dicionário
    received_headers = dict(request.headers)
    
    # Tenta pegar o cabeçalho de autorização específico
    auth_header = request.headers.get('Authorization')
    
    # Monta a string que esperamos receber (sem mostrar a chave real)
    expected_key_format = f"Bearer {INTERNAL_API_KEY}" if INTERNAL_API_KEY else None
    
    # Compara a chave recebida com a chave esperada
    keys_match = (auth_header == expected_key_format)

    # Prepara uma resposta JSON detalhada para o debug
    debug_response = {
        "debug_mode": True,
        "message": "Inspecionando a requisição recebida...",
        "received_authorization_header": auth_header,
        "is_internal_key_set_on_render": bool(INTERNAL_API_KEY),
        "are_keys_matching": keys_match,
        "all_received_headers": received_headers
    }

    # Retorna a resposta de debug com status 200 para que possamos vê-la no frontend
    return jsonify(debug_response), 200

# Rota raiz para verificar se o serviço está online
@app.route('/')
def home():
    return "Serviço de Geração de Áudio (Modo de Debug) - Online"

# Bloco para rodar a aplicação (usado pelo Gunicorn no Render)
if __name__ == '__main__':
    # A porta é definida pelo Render através de uma variável de ambiente
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
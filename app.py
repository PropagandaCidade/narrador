import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Pega a chave secreta que o Render DEVERIA ter
INTERNAL_API_KEY_EXPECTED = os.getenv("INTERNAL_API_KEY")

@app.route('/generate', methods=['POST'])
def debug_request_inspector():
    """
    Esta rota não gera áudio. Ela apenas inspeciona a requisição
    recebida e retorna um relatório detalhado.
    """
    # Captura todos os cabeçalhos recebidos
    received_headers = dict(request.headers)
    
    # Captura o cabeçalho de autorização específico
    auth_header_received = request.headers.get('Authorization')

    # Retorna um relatório JSON completo para o PHP
    return jsonify({
        "debug_report": True,
        "message": "Relatório de inspeção do servidor Python.",
        "was_internal_key_found_on_render": bool(INTERNAL_API_KEY_EXPECTED),
        "received_authorization_header": auth_header_received,
        "all_received_headers": received_headers
    }), 200

@app.route('/')
def home():
    return "Serviço de Inspeção - Online"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
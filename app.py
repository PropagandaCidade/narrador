# app.py - VERSÃO DE DIAGNÓSTICO
import os
import sys
import logging
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- INÍCIO DO CÓDIGO DE DIAGNÓSTICO ---
try:
    # Tenta importar o pacote que está causando o problema
    import google.generativeai as genai
    # Se a importação funcionar, pegamos a versão e o caminho
    version = getattr(genai, '__version__', 'não encontrada')
    path = getattr(genai, '__file__', 'não encontrado')
    status_message = f"SUCESSO: 'google.generativeai' importado. Versão: {version}, Caminho: {path}"
    
    # Adicionalmente, vamos verificar o pacote 'google' raiz
    import google
    google_path = getattr(google, '__path__', 'não encontrado')
    status_message += f" | Caminho do pacote 'google' raiz: {google_path}"

except ImportError as e:
    # Se a importação falhar, capturamos o erro
    status_message = f"FALHA NA IMPORTAÇÃO: {e}"
except Exception as e:
    # Captura outros erros inesperados durante a tentativa
    status_message = f"ERRO INESPERADO: {e}"

# Também logamos os caminhos de sistema do Python para ver onde ele está procurando pacotes
python_path = sys.path
# --- FIM DO CÓDIGO DE DIAGNÓSTICO ---

@app.route('/')
def home():
    return "Serviço de Narração - MODO DE DIAGNÓSTICO."

@app.route('/api/generate-audio', methods=['POST'])
def debug_endpoint():
    logger.info("Recebendo solicitação em modo de diagnóstico.")
    
    # Retorna as informações que coletamos em vez de gerar áudio
    return jsonify({
        "status": "MODO DE DIAGNÓSTICO ATIVO",
        "import_status": status_message,
        "python_sys_path": python_path,
        "error_original_que_estamos_investigando": "module 'google.genai' has no attribute 'configure'"
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
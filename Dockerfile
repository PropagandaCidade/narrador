# Usamos uma imagem oficial e leve do Python, travando na versão 3.11
FROM python:3.11-slim

# Definimos o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copiamos o arquivo de dependências
COPY requirements.txt .

# --- COMANDO DE DIAGNÓSTICO ---
# 1. Instala as dependências
# 2. Lista TUDO que foi instalado para vermos no log
# 3. Tenta importar o 'genai' IMEDIATAMENTE após a instalação
RUN pip install --no-cache-dir -r requirements.txt \
    && echo "--- PIP LIST DEPAVOLTA DA INSTALAÇÃO ---" \
    && pip list \
    && echo "--- TESTANDO A IMPORTAÇÃO DENTRO DO BUILD ---" \
    && python -c "from google import genai; print('SUCESSO: O módulo genai foi importado corretamente durante o build!')"

# Copiamos todo o resto do código da sua aplicação
COPY . .

# Define o comando que vai iniciar a sua aplicação.
CMD gunicorn app:app --bind 0.0.0.0:$PORT
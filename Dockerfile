# Usamos uma imagem oficial e leve do Python, travando na versão 3.11
FROM python:3.11-slim

# Definimos o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copiamos o arquivo de dependências
COPY requirements.txt .

# --- A CORREÇÃO CIRÚRGICA ---
# 1. Instala as dependências (incluindo o pacote conflitante)
# 2. IMEDIATAMENTE DESINSTALA o 'google-api-python-client' que causa o conflito.
# 3. Testa a importação novamente para garantir que o ambiente agora está limpo.
RUN pip install --no-cache-dir -r requirements.txt \
    && echo "--- DESINSTALANDO PACOTE CONFLITANTE ---" \
    && pip uninstall -y google-api-python-client \
    && echo "--- TESTANDO IMPORTAÇÃO APÓS A CORREÇÃO ---" \
    && python -c "from google import genai; print('SUCESSO! O MÓDULO GENAI FOI IMPORTADO CORRETAMENTE APÓS A CORREÇÃO!')"

# Copiamos todo o resto do código da sua aplicação
COPY . .

# Define o comando que vai iniciar a sua aplicação.
CMD gunicorn app:app --bind 0.0.0.0:$PORT
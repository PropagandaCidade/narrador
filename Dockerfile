# Usamos uma imagem oficial e leve do Python, travando na versão 3.11
FROM python:3.11-slim

# Definimos o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copiamos o arquivo de dependências
COPY requirements.txt .

# --- A CIRURGIA DE FORÇA BRUTA ---
# 1. Instala tudo, sabendo que vai criar um conflito.
# 2. USA rm -rf PARA APAGAR COMPLETAMENTE a pasta 'google' corrompida.
# 3. REINSTALA a biblioteca correta em um ambiente agora limpo.
# 4. TESTA a importação para provar que a cirurgia funcionou.
RUN pip install --no-cache-dir -r requirements.txt \
    && echo "--- LIMPANDO O NAMESPACE 'google' FORÇADAMENTE ---" \
    && rm -rf /usr/local/lib/python3.11/site-packages/google \
    && echo "--- REINSTALANDO 'google-generativeai' EM UM AMBIENTE LIMPO ---" \
    && pip install --no-cache-dir --force-reinstall google-generativeai \
    && echo "--- TESTE FINAL DE IMPORTAÇÃO PÓS-CIRURGIA ---" \
    && python -c "from google import genai; print('VITÓRIA! O namespace foi limpo e a importação funcionou!')"

# Copiamos todo o resto do código da sua aplicação
COPY . .

# Define o comando que vai iniciar a sua aplicação.
CMD gunicorn app:app --bind 0.0.0.0:$PORT
# Usamos uma imagem oficial e leve do Python, travando na versão 3.11
FROM python:3.11-slim

# Definimos o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copiamos o arquivo de dependências primeiro para otimizar o cache do Docker
COPY requirements.txt .

# Instalamos as dependências. Este comando é agora explícito e garantido.
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo o resto do código da sua aplicação
COPY . .

# Define o comando que vai iniciar a sua aplicação.
# Ele usa a variável $PORT que o Railway fornece automaticamente.
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
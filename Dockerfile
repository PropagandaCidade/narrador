# Usa a imagem oficial do Python mais recente como base
FROM python:3.11.9-slim

# Define o diretório de trabalho DENTRO do contêiner.
WORKDIR /app

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o restante do código do seu projeto local para o diretório /app no contêiner.
COPY . .

# Informa ao Docker que o contêiner vai escutar na porta 8080
EXPOSE 8080

# Comando para rodar o servidor Gunicorn quando o contêiner iniciar.
# O Railway DEVE usar este CMD se nenhum "Start Command" explícito for fornecido.
CMD ["gunicorn", "-c", "/app/gunicorn.conf.py", "app:app"]
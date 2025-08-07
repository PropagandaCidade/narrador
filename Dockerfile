# Usa a imagem oficial do Python mais recente como base
# Baseado no seu runtime.txt, usamos 3.11.9
FROM python:3.11.9-slim

# Define o diretório de trabalho DENTRO do contêiner.
# Isso significa que todos os comandos seguintes (COPY, RUN, CMD) serão executados a partir de /app.
WORKDIR /app

# Copia o arquivo de requisitos para dentro do contêiner e o instala.
# Copiamos primeiro apenas o requirements.txt para aproveitar o cache do Docker.
# Se o requirements.txt não mudar, esta camada não será reconstruída.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia TODO o restante do código do seu projeto local para o diretório /app no contêiner.
# Isso inclui app.py, gunicorn.conf.py (se você o criou ou já tinha), e qualquer outro arquivo.
COPY . .

# Informa ao Docker que o contêiner vai escutar na porta especificada pelo Gunicorn (configurada em gunicorn.conf.py)
# Geralmente é 8080, mas o Railway gerencia a porta externa.
EXPOSE 8080

# Comando para rodar o servidor Gunicorn quando o contêiner iniciar.
# -c /app/gunicorn.conf.py: Diz para o Gunicorn usar o arquivo de configuração que está em /app/gunicorn.conf.py dentro do contêiner.
# app:app: Indica que o aplicativo Gunicorn deve ser encontrado no módulo 'app' (seu app.py) e a instância do Flask dentro dele é chamada 'app'.
CMD ["gunicorn", "-c", "/app/gunicorn.conf.py", "app:app"]
# gunicorn.conf.py

import os

# Onde seu aplicativo Flask está. Geralmente 'app:app' se seu arquivo principal for app.py
# e a instância do Flask dentro dele se chama 'app'.
# Se seu arquivo principal fosse 'wsgi.py' e a instância do Flask fosse 'application', seria 'wsgi:application'.
# Pelo seu app.py, 'app:app' está correto.
bind = "0.0.0.0:8080" # O Gunicorn vai ouvir na porta 8080 (o Railway mapeia isso internamente)

# Número de Workers (processos de worker)
# Uma regra comum é (2 * número_de_cores) + 1
workers = 3

# Configurações de log (opcional, mas bom para depuração)
loglevel = "info" # Pode ser 'debug', 'info', 'warning', 'error', 'critical'
accesslog = "-"     # Log de acesso para stdout (visível nos logs do Railway)
errorlog = "-"      # Log de erro para stdout (visível nos logs do Railway)

# Se você quer um worker que execute seu código em vez de apenas gerenciar outros workers
# worker_class = "sync" # ou "gevent", "eventlet" se você estiver usando bibliotecas assíncronas

# O caminho para o seu app.py (e a instância do Flask dentro dele)
# Pelo que você mostrou, deve ser 'app:app'
# worker_connections = 1000 # Número máximo de conexões simultâneas por worker

# Se você tem um ambiente específico que quer configurar para o Gunicorn:
# env = "production"
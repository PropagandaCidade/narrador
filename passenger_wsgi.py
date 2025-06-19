# passenger_wsgi.py

import sys
import os

# Adiciona o diretório da aplicação ao path do Python
# para que ele possa encontrar 'app.py'
sys.path.insert(0, os.path.dirname(__file__))

# Importa a instância 'app' do seu arquivo 'app.py'
from app import app as application
# text_utils.py
# -------------------------------------------------
# "Cérebro Auxiliar" de Processamento de Texto para o Serviço de Narração.
# Garante a pronúncia correta de termos gramaticalmente ambíguos.
# -------------------------------------------------

import re

def correct_grammar_for_grams(text: str) -> str:
    """
    Força a pronúncia masculina para "gramas" no TTS, convertendo os dígitos
    problemáticos para texto por extenso. Ex: "400 gramas" -> "quatrocentos gramas".
    """
    # Mapeamento apenas dos números que geram ambiguidade de gênero.
    number_to_masculine_word = {
        '2': 'dois',
        '200': 'duzentos',
        '300': 'trezentos',
        '400': 'quatrocentos',
        '500': 'quinhentos',
        '600': 'seiscentos',
        '700': 'setecentos',
        '800': 'oitocentos',
        '900': 'novecentos',
    }
    
    # Padrão de regex para encontrar um dos números mapeados seguido por "grama" ou "gramas".
    pattern = re.compile(r"\b(" + "|".join(number_to_masculine_word.keys()) + r")\s+(gramas?)\b", re.IGNORECASE)

    def repl_func(match):
        number_digit = match.group(1)
        unit_word = match.group(2)
        
        # Substitui o dígito pela palavra masculina correspondente.
        return f"{number_to_masculine_word[number_digit]} {unit_word}"

    return pattern.sub(repl_func, text)
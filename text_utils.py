# text_utils.py
# -------------------------------------------------
# "Cérebro Auxiliar" de Processamento de Texto para o Serviço de Narração.
# Garante a pronúncia correta de termos gramaticalmente ambíguos.
# VERSÃO 2.0 - Adiciona normalização para preços, porcentagens e outros símbolos.
# -------------------------------------------------

import re

def correct_grammar_for_grams(text: str) -> str:
    """
    Normaliza o texto para o TTS, forçando a pronúncia correta de "gramas",
    preços, porcentagens e outros símbolos ambíguos.
    """
    
    # --- [INÍCIO DA LÓGICA ORIGINAL PRESERVADA] ---
    # Mapeamento para ambiguidade de gênero com "gramas".
    number_to_masculine_word = {
        '2': 'dois', '200': 'duzentos', '300': 'trezentos', '400': 'quatrocentos',
        '500': 'quinhentos', '600': 'seiscentos', '700': 'setecentos',
        '800': 'oitocentos', '900': 'novecentos',
    }
    
    pattern = re.compile(r"\b(" + "|".join(number_to_masculine_word.keys()) + r")\s+(gramas?)\b", re.IGNORECASE)

    def repl_func(match):
        number_digit = match.group(1)
        unit_word = match.group(2)
        return f"{number_to_masculine_word[number_digit]} {unit_word}"

    processed_text = pattern.sub(repl_func, text)
    # --- [FIM DA LÓGICA ORIGINAL PRESERVADA] ---


    # --- [INÍCIO DA NOVA LÓGICA DE NORMALIZAÇÃO] ---
    # As regras são aplicadas em sequência no texto já processado.
    
    # Converte R$ 19,90 para "19 reais e 90 centavos"
    processed_text = re.sub(r'R\$\s*(\d+),(\d{2})', r'\1 reais e \2 centavos', processed_text)
    
    # Converte 19,90 (sem R$) para "19 vírgula 90" (para evitar erros de leitura)
    processed_text = re.sub(r'(\d+),(\d+)', r'\1 vírgula \2', processed_text)
    
    # Converte 50% para "50 por cento"
    processed_text = re.sub(r'(\d+)%', r'\1 por cento', processed_text)
    
    # Remove ou substitui caracteres que podem confundir a IA
    processed_text = processed_text.replace('*', ' ')
    processed_text = processed_text.replace('-', ' ') # Evita pausas estranhas
    
    # Garante que não haja espaços duplos resultantes das substituições
    processed_text = re.sub(r'\s+', ' ', processed_text).strip()
    # --- [FIM DA NOVA LÓGICA DE NORMALIZAÇÃO] ---
    
    return processed_text
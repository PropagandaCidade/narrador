# text_utils.py
# VERSÃO: 3.0 (Simplificado)
# DESCRIÇÃO: Este arquivo foi neutralizado. A lógica de normalização de texto
# foi centralizada no 'TextNormalizer.php' da aplicação principal.
# Este script agora apenas repassa o texto sem modificações para evitar conflitos.

import re
from typing import Set

def correct_grammar_for_grams(text: str) -> str:
    """
    NEUTRALIZADO: Esta função não faz mais correções gramaticais.
    Apenas retorna o texto original.
    """
    return text

def normalize_text(text: str) -> str:
    """
    NEUTRALIZADO: Esta função não faz mais normalizações de símbolos.
    Apenas retorna o texto original.
    """
    return text

def whitelist_tags_only(s: str, allowed_names: Set[str]) -> str:
    """
    (FUNÇÃO MANTIDA) Remove quaisquer tags que não estejam na lista de permissão como uma medida de segurança.
    """
    if not allowed_names:
        # Se não há tags permitidas, remove todas.
        return re.sub(r"<[^>]+>", "", s)

    def _repl(m: re.Match) -> str:
        # Extrai o nome da tag, removendo a barra inicial se for uma tag de fechamento
        tag_content = m.group(1)
        tag_name = tag_content.split()[0].lstrip('/')
        return m.group(0) if tag_name in allowed_names else ""

    # Padrão aprimorado para capturar o nome da tag corretamente
    return re.sub(r"<(/?[a-zA-Z0-9_]+(?: [^>]+)?)>", _repl, s)

# Você pode adicionar um alias para a função principal, se seu app.py a chamar
process_text = normalize_text
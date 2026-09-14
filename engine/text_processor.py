import re
import unicodedata
from typing import Tuple

class TextProcessor:
    """Processador de texto fonético e analisador de intenções de voz."""

    @staticmethod
    def normalizar(texto: str) -> str:
        """Remove acentos, caracteres especiais e converte para minúsculas."""
        if not texto:
            return ""
        texto_sem_acento = ''.join(
            c for c in unicodedata.normalize('NFD', texto)
            if unicodedata.category(c) != 'Mn'
        )
        return re.sub(r'[^\w\s]', ' ', texto_sem_acento.lower()).strip()

    @classmethod
    def eh_comando_saida(cls, texto: str) -> bool:
        """
        Detecta comandos flexíveis para encerrar ou pausar a conversa e entrar em standby.
        """
        norm = cls.normalizar(texto)
        padroes = [
            r'\b(sai|saia|sair|encerra|encerrar|finaliza|finalizar|fechar?|para|parar|cancela|cancelar|pausa|pausar)\s+(da|de|do|dessa|desta|a|o)?\s*(conversa|chat|sessao|atendimento)\b',
            r'\b(quero|vou|pode|favor|vamos)?\s*(sair|encerrar|parar|dormir|desativar|desligar)\b',
            r'\b(tchau|adeus|ate mais|ate logo|bye|falou)\b'
        ]
        return any(re.search(p, norm) for p in padroes)

    @classmethod
    def extrair_wake_word(cls, texto: str) -> Tuple[bool, str]:
        """
        Verifica se o texto contém a palavra de ativação 'AGY' (incluindo variações fonéticas como adaj, adai, adji, agi).
        Retorna (True, comando_restante) ou (False, "").
        """
        norm = cls.normalizar(texto)
        padroes = [
            r'\b(ei|hey|ola|oi|ok|e\s*ai)?\s*(agy|adaj|adai|adji|adje|adjy|adgi|adgy|ajai|adjai|adaji|agi|age|aggie|aje|aji|ajy|eigi|eiji|edge|edgy|a\s*g\s*y|antigravity)\b'
        ]
        for p in padroes:
            match = re.search(p, norm)
            if match:
                resto = norm[match.end():].strip()
                return True, resto
        return False, ""

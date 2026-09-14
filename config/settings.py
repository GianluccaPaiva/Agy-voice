import os

# Diretório e arquivo de configuração
SETTING_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "setting")
CONFIG_FILE = os.path.join(SETTING_DIR, "config.json")
OLD_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# Vozes disponíveis no edge-tts
VOZES_DISPONIVEIS = {
    "Antônio (PT-BR Masculino)": "pt-BR-AntonioNeural",
    "Francisca (PT-BR Feminino)": "pt-BR-FranciscaNeural",
    "Thalita (PT-BR Multilíngue)": "pt-BR-ThalitaMultilingualNeural",
    "Duarte (PT-PT Portugal)": "pt-PT-DuarteNeural",
    "Raquel (PT-PT Portugal)": "pt-PT-RaquelNeural",
    "Guy (EN-US Masculino)": "en-US-GuyNeural",
    "Aria (EN-US Feminino)": "en-US-AriaNeural"
}

# Modelos do Whisper disponíveis para STT
MODELOS_WHISPER_DISPONIVEIS = {
    "Tiny (Ultra Rápido • ~75 MB)": "tiny",
    "Base (Equilibrado • ~150 MB)": "base",
    "Small (Alta Precisão • ~480 MB)": "small",
    "Medium (Estúdio • ~1.5 GB)": "medium",
    "Turbo (Máxima Precisão • ~1.6 GB)": "turbo"
}

# Paleta rápida de cores para o Color Wheel
PRESETS_CORES_CIRCULO = [
    ("#06b6d4", "Ciano"),
    ("#10b981", "Esmeralda"),
    ("#3b82f6", "Azul Elétrico"),
    ("#7c3aed", "Roxo"),
    ("#ec4899", "Rosa Neon"),
    ("#f59e0b", "Dourado"),
    ("#ef4444", "Vermelho"),
    ("#ffffff", "Branco")
]

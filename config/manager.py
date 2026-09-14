import json
import os
from dataclasses import dataclass, asdict
from config.settings import SETTING_DIR, CONFIG_FILE, OLD_CONFIG_FILE

@dataclass
class AppConfig:
    tipo_de_voz: str = "Antônio (PT-BR Masculino)"
    transparencia: float = 1.0
    ultimo_estado: str = "acordado"  # "acordado" ou "standby"
    fixar_no_topo: bool = False
    painel_transcricao_aberto: bool = True
    cor_acordado: str = "#06b6d4"
    cor_standby: str = "#7c3aed"
    modelo_whisper: str = "Base (Equilibrado • ~150 MB)"

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        valid_keys = {k for k in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

class ConfigManager:
    """Gerenciador de configurações persistentes com suporte a migração automática."""
    
    @staticmethod
    def carregar() -> AppConfig:
        os.makedirs(SETTING_DIR, exist_ok=True)
        
        # Migração automática caso ainda exista config legado na raiz
        if not os.path.exists(CONFIG_FILE) and os.path.exists(OLD_CONFIG_FILE):
            try:
                with open(OLD_CONFIG_FILE, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(dados, f, indent=4, ensure_ascii=False)
                os.remove(OLD_CONFIG_FILE)
                return AppConfig.from_dict(dados)
            except Exception:
                pass

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    return AppConfig.from_dict(dados)
            except Exception as e:
                print(f"⚠️ Erro ao ler setting/config.json: {e}")

        config_padrao = AppConfig()
        ConfigManager.salvar(config_padrao)
        return config_padrao

    @staticmethod
    def salvar(config: AppConfig) -> None:
        try:
            os.makedirs(SETTING_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(config), f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro ao salvar setting/config.json: {e}")

import asyncio
import threading
from config import ConfigManager, VOZES_DISPONIVEIS, MODELOS_WHISPER_DISPONIVEIS
from core import global_event_bus
from engine import VoiceController
from ui import MainWindow

def main():
    # 1. Carrega configurações persistentes
    config = ConfigManager.carregar()
    
    voz_id = VOZES_DISPONIVEIS.get(config.tipo_de_voz, "pt-BR-AntonioNeural")
    whisper_id = MODELOS_WHISPER_DISPONIVEIS.get(config.modelo_whisper, "base")
    estado_ativo = (config.ultimo_estado != "standby")

    # 2. Inicializa o Controlador de Voz Desacoplado
    controller = VoiceController(
        event_bus=global_event_bus,
        estado_inicial_conversa=estado_ativo,
        voz_inicial=voz_id,
        modelo_whisper_inicial=whisper_id
    )

    # 3. Executa o loop de áudio em thread dedicada com asyncio
    audio_thread = threading.Thread(
        target=lambda: asyncio.run(controller.executar_loop()),
        daemon=True
    )
    audio_thread.start()

    # 4. Inicializa a Interface Desktop
    app = MainWindow(
        event_bus=global_event_bus,
        voice_controller=controller,
        config=config
    )
    app.mainloop()

if __name__ == "__main__":
    main()

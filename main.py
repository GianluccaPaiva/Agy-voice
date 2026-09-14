import asyncio
from config import ConfigManager, VOZES_DISPONIVEIS, MODELOS_WHISPER_DISPONIVEIS
from core import (
    global_event_bus,
    AppState,
    StateChangedEvent,
    ChatMessageEvent,
    VADStatusEvent,
    ModelLoadProgressEvent
)
from engine import VoiceController

def main():
    config = ConfigManager.carregar()
    voz_id = VOZES_DISPONIVEIS.get(config.tipo_de_voz, "pt-BR-AntonioNeural")
    whisper_id = MODELOS_WHISPER_DISPONIVEIS.get(config.modelo_whisper, "base")
    estado_ativo = (config.ultimo_estado != "standby")

    print("\n" + "=" * 60)
    print("🎙️  AGY Voice Frontend • Versão Terminal / CLI")
    print(" 💡 Diga 'sair da conversa' para pausar a sessão.")
    print(" 💡 Diga 'AGY' para reativar quando estiver em standby.")
    print(" 💡 Você pode falar por cima do assistente para interrompê-lo!")
    print(" Pressione Ctrl+C para encerrar.")
    print("=" * 60 + "\n")

    # Observer para imprimir no terminal
    def on_state(event: StateChangedEvent):
        if event.new_state == AppState.STANDBY:
            print("\n💤 [Modo Standby] Aguardando comando 'AGY' para acordar...")
        elif event.new_state == AppState.LISTENING:
            print("\n👂 [Ouvindo microfone] Pode falar...")
        elif event.new_state == AppState.THINKING:
            print("⏳ Processando com agy CLI...")
        elif event.new_state == AppState.SPEAKING:
            print("🔊 Falando resposta...")

    def on_chat(event: ChatMessageEvent):
        if event.sender == "user":
            print(f"\n👤 Você: \"{event.message}\"")
        elif event.sender == "agy":
            print(f"\n🤖 agy:\n{event.message}\n")
        else:
            print(f"⚙️  {event.message}")

    def on_vad(event: VADStatusEvent):
        if "Gravando" in event.status_text:
            print(f"🎤 {event.status_text}")

    def on_progress(event: ModelLoadProgressEvent):
        print(f"📦 {event.message}")

    global_event_bus.subscribe(StateChangedEvent, on_state)
    global_event_bus.subscribe(ChatMessageEvent, on_chat)
    global_event_bus.subscribe(VADStatusEvent, on_vad)
    global_event_bus.subscribe(ModelLoadProgressEvent, on_progress)

    controller = VoiceController(
        event_bus=global_event_bus,
        estado_inicial_conversa=estado_ativo,
        voz_inicial=voz_id,
        modelo_whisper_inicial=whisper_id
    )

    try:
        asyncio.run(controller.executar_loop())
    except KeyboardInterrupt:
        print("\n👋 Encerrando AGY Voice Frontend...")

if __name__ == "__main__":
    main()

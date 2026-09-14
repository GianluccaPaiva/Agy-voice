import asyncio
import uuid
import numpy as np
from typing import Optional, List
from core.states import AppState
from core.events import (
    StateChangedEvent,
    VolumeLevelEvent,
    VADStatusEvent,
    ChatMessageEvent,
    ModelLoadProgressEvent,
    PermissionRequestEvent,
    PermissionResponseEvent
)
from core.event_bus import EventBus, global_event_bus
from engine.vad import AudioRecorderVAD, AcousticPreFilter
from engine.stt import FasterWhisperSTT
from engine.tts import EdgeTTSEngine
from engine.agy_bridge import AgyBridge, AgyExecutionResult
from engine.text_processor import TextProcessor

class VoiceController:
    """
    Controlador central do Pipeline de Áudio, Máquina de Estados e Interceptação de Permissões.
    Emite eventos tipados via EventBus para total desacoplamento da interface.
    """
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        estado_inicial_conversa: bool = True,
        voz_inicial: str = "pt-BR-AntonioNeural",
        modelo_whisper_inicial: str = "base"
    ):
        self.bus = event_bus or global_event_bus
        self.em_conversa = estado_inicial_conversa
        self.primeira_vez = True
        self.executando = True

        # Controle de Interceptação de Permissão
        self.permissao_pendente_id: Optional[str] = None
        self.fila_resposta_permissao: asyncio.Queue = asyncio.Queue()
        self.bus.subscribe(PermissionResponseEvent, self._ao_receber_resposta_permissao_evento)

        # Componentes do Pipeline
        self.vad = AudioRecorderVAD(
            volume_callback=lambda v: self.bus.publish(VolumeLevelEvent(v)),
            status_callback=lambda s: self.bus.publish(VADStatusEvent(s))
        )
        self.stt = FasterWhisperSTT(
            model_name=modelo_whisper_inicial,
            on_progress=lambda m, l, msg: self.bus.publish(ModelLoadProgressEvent(m, l, msg))
        )
        self.tts = EdgeTTSEngine(voz_inicial=voz_inicial)
        self.bridge = AgyBridge()

    def _ao_receber_resposta_permissao_evento(self, event: PermissionResponseEvent):
        """Callback acionado quando o usuário responde pelo botão da interface."""
        if self.permissao_pendente_id == event.request_id:
            try:
                self.fila_resposta_permissao.put_nowait(event.approved)
            except Exception as e:
                print(f"⚠️ Erro ao enfileirar resposta de permissão: {e}")

    def alternar_estado_standby(self) -> None:
        """Alterna entre Standby e Ativo a partir de um comando de UI ou atalho."""
        self.em_conversa = not self.em_conversa
        self.vad.interromper = True
        self.primeira_vez = True

        if self.em_conversa:
            self.bus.publish(StateChangedEvent(AppState.LISTENING))
            self.bus.publish(VADStatusEvent("👂 Ouvindo microfone..."))
            self.bus.publish(ChatMessageEvent("system", "⚡ AGY acordado pelo botão."))
        else:
            self.bus.publish(StateChangedEvent(AppState.STANDBY))
            self.bus.publish(VADStatusEvent("💤 Standby: Diga 'AGY'..."))
            self.bus.publish(ChatMessageEvent("system", "💤 AGY colocado em standby pelo botão."))

    def alternar_mudo(self) -> bool:
        """Alterna estado de mudo do microfone."""
        self.vad.microfone_mutado = not self.vad.microfone_mutado
        return self.vad.microfone_mutado

    def trocar_voz(self, nova_voz: str) -> None:
        self.tts.voz_atual = nova_voz

    def trocar_modelo_whisper(self, novo_modelo: str) -> bool:
        return self.stt.trocar_modelo(novo_modelo)

    async def _tratar_solicitacao_permissao(self, resultado_agy: AgyExecutionResult) -> str:
        """
        Intercepta a solicitação de autorização de ferramenta do agy CLI.
        Notifica a interface gráfica com botões interativos e pergunta ao usuário por voz.
        Aceita respostas tanto por voz ('Yes', 'Sim', 'Autorizo', 'Pode executar') quanto por clique.
        """
        req_id = uuid.uuid4().hex[:8]
        self.permissao_pendente_id = req_id

        # Limpa fila de respostas pendentes
        while not self.fila_resposta_permissao.empty():
            try:
                self.fila_resposta_permissao.get_nowait()
            except Exception:
                break

        # Dispara evento para a interface criar o card com botões Sim / Não
        self.bus.publish(StateChangedEvent(AppState.WAITING_PERMISSION))
        self.bus.publish(VADStatusEvent("⚠️ Autorização necessária: Diga 'Yes'/'Sim' ou clique"))
        self.bus.publish(PermissionRequestEvent(
            request_id=req_id,
            action_type=resultado_agy.action_type,
            description=resultado_agy.action_description,
            details=resultado_agy.action_details
        ))

        # Formula a pergunta falada concisa
        detalhe_falado = resultado_agy.action_details.strip()
        if len(detalhe_falado) > 50:
            detalhe_falado = detalhe_falado[:50] + "..."

        if detalhe_falado:
            pergunta_fala = f"O AGY solicita permissão para {resultado_agy.action_description}: {detalhe_falado}. Você autoriza?"
        else:
            pergunta_fala = f"O AGY solicita permissão para {resultado_agy.action_description}. Você autoriza?"

        self.bus.publish(StateChangedEvent(AppState.SPEAKING))
        await self.tts.falar(pergunta_fala, permitir_interrupcao=True)

        self.bus.publish(StateChangedEvent(AppState.WAITING_PERMISSION))
        self.bus.publish(VADStatusEvent("👂 Aguardando resposta: Diga 'Sim/Yes' ou 'Não'..."))

        aprovado: Optional[bool] = None
        while self.executando and aprovado is None:
            # 1. Verifica se houve clique em botão da UI
            if not self.fila_resposta_permissao.empty():
                aprovado = self.fila_resposta_permissao.get_nowait()
                break

            # 2. Captura áudio do usuário respondendo por voz
            audio_array = self.vad.gravar(threshold=0.018, silencio_limite=0.8)

            # Verifica novamente se o usuário clicou no botão durante a gravação
            if not self.fila_resposta_permissao.empty():
                aprovado = self.fila_resposta_permissao.get_nowait()
                break

            if audio_array is None or not AcousticPreFilter.validar_presenca_voz(audio_array):
                await asyncio.sleep(0.05)
                continue

            texto_resposta = self.stt.transcrever(audio_array, modo_rapido=True)
            if not texto_resposta:
                continue

            print(f"[Voz capturada para permissão]: '{texto_resposta}'")
            if TextProcessor.eh_confirmacao(texto_resposta):
                aprovado = True
                self.bus.publish(ChatMessageEvent("user", f"✔ \"{texto_resposta}\" (Autorizado por voz)"))
                break
            elif TextProcessor.eh_negacao(texto_resposta):
                aprovado = False
                self.bus.publish(ChatMessageEvent("user", f"✖ \"{texto_resposta}\" (Recusado por voz)"))
                break

        self.permissao_pendente_id = None

        if aprovado:
            self.bus.publish(ChatMessageEvent("system", "⚡ Permissão concedida pelo usuário. Executando ação no AGY..."))
            self.bus.publish(StateChangedEvent(AppState.THINKING))
            res_execucao = await self.bridge.executar(
                "Sim, permissão concedida pelo usuário. Prossiga e execute a ação agora.",
                primeira_interacao=False,
                skip_permissions=True
            )
            return res_execucao.response_text or "Ação executada com sucesso."
        else:
            self.bus.publish(ChatMessageEvent("system", "🚫 Permissão recusada pelo usuário. Cancelando ação..."))
            self.bus.publish(StateChangedEvent(AppState.THINKING))
            res_execucao = await self.bridge.executar(
                "Permissão negada pelo usuário. Prossiga sem executar essa ação e responda ao usuário.",
                primeira_interacao=False,
                skip_permissions=False
            )
            return res_execucao.response_text or "Ação cancelada a seu pedido."

    async def executar_loop(self) -> None:
        """Loop principal do assistente de voz."""
        frames_interrupcao: Optional[List[np.ndarray]] = None
        falando_inicial: bool = False

        while self.executando:
            try:
                # ----------------------------------------------------
                # MODO 1: STANDBY / DORMINDO
                # ----------------------------------------------------
                if not self.em_conversa:
                    self.bus.publish(StateChangedEvent(AppState.STANDBY))
                    self.bus.publish(VADStatusEvent("💤 Standby: Diga 'AGY'..."))
                    
                    audio_array = self.vad.gravar(threshold=0.018, silencio_limite=1.0)
                    if not self.executando or audio_array is None:
                        continue

                    if not AcousticPreFilter.validar_presenca_voz(audio_array):
                        continue

                    texto = self.stt.transcrever(audio_array, modo_rapido=True)
                    if not texto:
                        continue

                    print(f"[Standby escutou]: '{texto}'")
                    acordou, extra = TextProcessor.extrair_wake_word(texto)

                    if acordou:
                        self.em_conversa = True
                        self.primeira_vez = True
                        self.bus.publish(StateChangedEvent(AppState.LISTENING))
                        self.bus.publish(ChatMessageEvent("user", f"⚡ Wake Word detectada: \"{texto}\""))

                        if extra:
                            texto_usuario = extra
                        else:
                            await self.tts.falar("Estou ouvindo. Como posso ajudar?", permitir_interrupcao=False)
                            continue
                    else:
                        continue
                else:
                    # ----------------------------------------------------
                    # MODO 2: ATIVO / EM CONVERSA
                    # ----------------------------------------------------
                    self.bus.publish(StateChangedEvent(AppState.LISTENING))
                    self.bus.publish(VADStatusEvent("👂 Ouvindo microfone..."))

                    audio_array = self.vad.gravar(
                        frames_iniciais=frames_interrupcao,
                        falando_inicial=falando_inicial
                    )
                    frames_interrupcao = None
                    falando_inicial = False

                    if not self.executando or audio_array is None:
                        continue

                    texto_usuario = self.stt.transcrever(audio_array)
                    if not texto_usuario:
                        continue

                    self.bus.publish(ChatMessageEvent("user", texto_usuario))

                    # Verifica saída da conversa
                    if TextProcessor.eh_comando_saida(texto_usuario):
                        self.em_conversa = False
                        self.primeira_vez = True
                        self.bus.publish(StateChangedEvent(AppState.STANDBY))
                        self.bus.publish(ChatMessageEvent("agy", "Conversa encerrada. Diga AGY quando quiser voltar."))
                        await self.tts.falar("Conversa encerrada. Diga AGY quando quiser falar comigo novamente.", permitir_interrupcao=False)
                        continue

                # ----------------------------------------------------
                # Processamento com o agy CLI
                # ----------------------------------------------------
                self.bus.publish(StateChangedEvent(AppState.THINKING))
                resultado_agy = await self.bridge.executar(texto_usuario, primeira_interacao=self.primeira_vez)
                self.primeira_vez = False

                if resultado_agy.requer_permissao:
                    resposta = await self._tratar_solicitacao_permissao(resultado_agy)
                else:
                    resposta = resultado_agy.response_text

                if not resposta:
                    resposta = "Comando processado."

                self.bus.publish(ChatMessageEvent("agy", resposta))

                # ----------------------------------------------------
                # Síntese e Fala com suporte a Barge-in
                # ----------------------------------------------------
                self.bus.publish(StateChangedEvent(AppState.SPEAKING))
                interrompido, chunks = await self.tts.falar(resposta, permitir_interrupcao=self.em_conversa)
                if interrompido:
                    frames_interrupcao = chunks
                    falando_inicial = True

            except Exception as e:
                print(f"⚠️ Erro no loop de voz: {e}")
                await asyncio.sleep(1)

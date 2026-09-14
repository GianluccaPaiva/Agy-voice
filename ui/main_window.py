import sys
import threading
import customtkinter as ctk
import pygame
from config.settings import VOZES_DISPONIVEIS, MODELOS_WHISPER_DISPONIVEIS
from config.manager import ConfigManager, AppConfig
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
from core.event_bus import EventBus
from engine.voice_controller import VoiceController
from ui.orb import GlowingOrbCanvas
from ui.chat_feed import ChatFeedComponent
from ui.settings_view import SettingsView
from ui.color_wheel import ajustar_saturacao_cor
from ui.tray import SystemTrayManager

class MainWindow(ctk.CTk):
    """Janela principal do AGY Voice Hub (Desktop Native)."""

    def __init__(self, event_bus: EventBus, voice_controller: VoiceController, config: AppConfig):
        super().__init__()
        self.bus = event_bus
        self.controller = voice_controller
        self.config = config

        self.em_modo_configuracoes = False
        self.current_state = AppState.LISTENING if self.config.ultimo_estado == "acordado" else AppState.STANDBY
        self.current_permission_req_id = ""

        self._configurar_janela()
        self._criar_layout()
        self._inscrever_eventos()

        # Inicia System Tray
        self.tray = SystemTrayManager(
            on_restaurar=lambda: self.after(0, self.restaurar_janela),
            on_alternar_standby=lambda: self.after(0, self.controller.alternar_estado_standby),
            on_encerrar=lambda: self.after(0, self.encerrar_definitivo),
            cor_inicial=self.config.cor_acordado
        )
        self.tray.iniciar()

        # Inicia animação do Orb
        self.orb_canvas.animar()
        self._atualizar_visual_estado(self.current_state)

        # Minimizar no 'X'
        self.protocol("WM_DELETE_WINDOW", self.minimizar_para_segundo_plano)

    def _configurar_janela(self):
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("AGY Voice Hub • Desktop Native")
        self.geometry("980x640" if self.config.painel_transcricao_aberto else "400x620")
        self.minsize(850 if self.config.painel_transcricao_aberto else 380, 560)
        self.configure(fg_color="#090d16")

        self.attributes('-alpha', self.config.transparencia)
        self.attributes('-topmost', self.config.fixar_no_topo)

    def _criar_layout(self):
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(0, weight=1)

        # ----------------------------------------------------
        # PAINEL ESQUERDO (ORB / SETTINGS)
        # ----------------------------------------------------
        self.frame_left = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=20, border_width=1, border_color="#1e293b")
        self.frame_left.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")

        # VIEW 1: PAINEL DO ORB
        self.frame_orb_view = ctk.CTkFrame(self.frame_left, fg_color="transparent")
        self.frame_orb_view.pack(fill="both", expand=True)

        # Header do Orb
        self.frame_header = ctk.CTkFrame(self.frame_orb_view, fg_color="transparent")
        self.frame_header.pack(fill="x", padx=16, pady=(16, 2))

        self.lbl_title = ctk.CTkLabel(
            self.frame_header,
            text="AGY Voice Hub",
            font=ctk.CTkFont(family="Plus Jakarta Sans", size=20, weight="bold"),
            text_color="#f8fafc"
        )
        self.lbl_title.pack(side="left")

        self.btn_settings = ctk.CTkButton(
            self.frame_header,
            text="⚙",
            width=32,
            height=32,
            command=self.alternar_modo_configuracoes,
            fg_color="#1e293b",
            hover_color="#334155",
            corner_radius=10,
            font=ctk.CTkFont(size=16)
        )
        self.btn_settings.pack(side="right")

        self.lbl_badge = ctk.CTkLabel(
            self.frame_orb_view,
            text="By Gianlucca Paiva",
            font=ctk.CTkFont(family="JetBrains Mono", size=10, weight="bold"),
            text_color="#06b6d4"
        )
        self.lbl_badge.pack(pady=(0, 4))

        # Canvas do Orb
        self.orb_canvas = GlowingOrbCanvas(
            self.frame_orb_view,
            cor_acordado=self.config.cor_acordado,
            cor_standby=self.config.cor_standby
        )
        self.orb_canvas.pack(pady=4)

        # Status
        self.lbl_state_title = ctk.CTkLabel(
            self.frame_orb_view,
            text="Iniciando...",
            font=ctk.CTkFont(family="Plus Jakarta Sans", size=17, weight="bold"),
            text_color="#a855f7"
        )
        self.lbl_state_title.pack(pady=(2, 2))

        self.lbl_vad_status = ctk.CTkLabel(
            self.frame_orb_view,
            text="Aguardando...",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.lbl_vad_status.pack(pady=(0, 6))

        # Mini Banner de Permissão Rápida (para quando em WAITING_PERMISSION)
        self.frame_quick_perm = ctk.CTkFrame(self.frame_orb_view, fg_color="#1e1b4b", corner_radius=10, border_width=1, border_color="#f59e0b")
        self.lbl_quick_perm = ctk.CTkLabel(self.frame_quick_perm, text="⚠️ Autorização Requerida", font=ctk.CTkFont(size=11, weight="bold"), text_color="#fbbf24")
        self.lbl_quick_perm.pack(pady=(4, 2), padx=8)
        self.frame_quick_btns = ctk.CTkFrame(self.frame_quick_perm, fg_color="transparent")
        self.frame_quick_btns.pack(fill="x", padx=6, pady=(0, 4))
        self.btn_q_yes = ctk.CTkButton(self.frame_quick_btns, text="✔ Sim", fg_color="#10b981", hover_color="#059669", height=24, font=ctk.CTkFont(size=11, weight="bold"), command=lambda: self._on_permission_response(self.current_permission_req_id, True))
        self.btn_q_yes.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_q_no = ctk.CTkButton(self.frame_quick_btns, text="✖ Não", fg_color="#ef4444", hover_color="#dc2626", height=24, font=ctk.CTkFont(size=11, weight="bold"), command=lambda: self._on_permission_response(self.current_permission_req_id, False))
        self.btn_q_no.pack(side="right", fill="x", expand=True, padx=2)

        # Seletor de Voz
        self.frame_voz = ctk.CTkFrame(self.frame_orb_view, fg_color="transparent")
        self.frame_voz.pack(fill="x", padx=20, pady=3)

        self.lbl_voz = ctk.CTkLabel(self.frame_voz, text="Voz:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#cbd5e1")
        self.lbl_voz.pack(side="left", padx=5)

        self.combo_voz = ctk.CTkComboBox(
            self.frame_voz,
            values=list(VOZES_DISPONIVEIS.keys()),
            command=self._ao_trocar_voz,
            fg_color="#1e293b",
            button_color="#3b82f6",
            border_color="#334155",
            dropdown_fg_color="#0f172a"
        )
        self.combo_voz.set(self.config.tipo_de_voz)
        self.combo_voz.pack(side="right", fill="x", expand=True, padx=5)

        # Botões de Ação
        self.frame_botoes = ctk.CTkFrame(self.frame_orb_view, fg_color="transparent")
        self.frame_botoes.pack(fill="x", padx=20, pady=(6, 12))

        self.btn_toggle_standby = ctk.CTkButton(
            self.frame_botoes,
            text="Alternar Standby",
            command=self.controller.alternar_estado_standby,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            corner_radius=12,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_toggle_standby.pack(fill="x", pady=3)

        self.btn_mute = ctk.CTkButton(
            self.frame_botoes,
            text="Mutar Microfone",
            command=self._ao_alternar_mudo,
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=12,
            font=ctk.CTkFont(size=12)
        )
        self.btn_mute.pack(fill="x", pady=3)

        self.btn_toggle_feed = ctk.CTkButton(
            self.frame_botoes,
            text="💬 Ocultar Transcrição" if self.config.painel_transcricao_aberto else "💬 Mostrar Transcrição",
            command=self._alternar_painel_transcricao,
            fg_color="#334155" if self.config.painel_transcricao_aberto else "#0284c7",
            hover_color="#475569" if self.config.painel_transcricao_aberto else "#0369a1",
            corner_radius=12,
            font=ctk.CTkFont(size=12)
        )
        self.btn_toggle_feed.pack(fill="x", pady=3)

        # VIEW 2: PAINEL DE CONFIGURAÇÕES INLINE
        self.settings_view = SettingsView(
            self.frame_left,
            config=self.config,
            on_voltar=self.alternar_modo_configuracoes,
            on_opacity_changed=self._ao_mudar_opacidade,
            on_color_changed=self._ao_mudar_cor,
            on_whisper_changed=self._ao_mudar_whisper,
            on_topmost_changed=self._ao_mudar_topmost,
            on_exit_app=self.encerrar_definitivo
        )

        # ----------------------------------------------------
        # PAINEL DIREITO (FEED DE CONVERSA)
        # ----------------------------------------------------
        self.chat_feed = ChatFeedComponent(self, on_permission_response=self._on_permission_response)
        if self.config.painel_transcricao_aberto:
            self.chat_feed.grid(row=0, column=1, padx=(0, 16), pady=16, sticky="nsew")
        else:
            self.chat_feed.grid_remove()
            self.grid_columnconfigure(1, weight=0)

    def _inscrever_eventos(self):
        """Inscreve os listeners thread-safe no EventBus."""
        self.bus.subscribe(StateChangedEvent, lambda e: self.after(0, self._on_state_changed, e))
        self.bus.subscribe(VolumeLevelEvent, lambda e: self.after(0, self._on_volume, e))
        self.bus.subscribe(VADStatusEvent, lambda e: self.after(0, self._on_vad_status, e))
        self.bus.subscribe(ChatMessageEvent, lambda e: self.after(0, self._on_chat_message, e))
        self.bus.subscribe(ModelLoadProgressEvent, lambda e: self.after(0, self._on_model_progress, e))
        self.bus.subscribe(PermissionRequestEvent, lambda e: self.after(0, self._on_permission_request, e))

    def _on_state_changed(self, event: StateChangedEvent):
        self.current_state = event.new_state
        self.orb_canvas.set_state(event.new_state)
        self._atualizar_visual_estado(event.new_state)
        
        if event.new_state != AppState.WAITING_PERMISSION:
            self.chat_feed.esconder_solicitacao_permissao()
            self.frame_quick_perm.pack_forget()

        self.config.ultimo_estado = "acordado" if self.controller.em_conversa else "standby"
        ConfigManager.salvar(self.config)

    def _on_volume(self, event: VolumeLevelEvent):
        self.orb_canvas.set_volume(event.volume)

    def _on_vad_status(self, event: VADStatusEvent):
        self.lbl_vad_status.configure(text=event.status_text)

    def _on_chat_message(self, event: ChatMessageEvent):
        self.chat_feed.adicionar_mensagem(event.sender, event.message)

    def _on_model_progress(self, event: ModelLoadProgressEvent):
        self.chat_feed.adicionar_mensagem("system", event.message)

    def _on_permission_request(self, event: PermissionRequestEvent):
        self.current_permission_req_id = event.request_id
        self.chat_feed.mostrar_solicitacao_permissao(event.request_id, event.description, event.details)
        self.frame_quick_perm.pack(fill="x", padx=20, pady=(0, 4))
        # Se a janela estiver minimizada, restaura para o usuário ver
        if self.state() == "iconic" or not self.winfo_viewable():
            self.restaurar_janela()

    def _on_permission_response(self, req_id: str, approved: bool):
        if req_id:
            self.bus.publish(PermissionResponseEvent(request_id=req_id, approved=approved))
            self.frame_quick_perm.pack_forget()

    def _atualizar_visual_estado(self, state: AppState):
        hover_acordado = ajustar_saturacao_cor(self.config.cor_acordado)
        hover_standby = ajustar_saturacao_cor(self.config.cor_standby)

        if state == AppState.STANDBY:
            self.lbl_state_title.configure(text="Modo Standby 💤", text_color=self.config.cor_standby)
            self.btn_toggle_standby.configure(text="Acordar AGY ⚡", fg_color=self.config.cor_acordado, hover_color=hover_acordado)
        elif state == AppState.LISTENING:
            self.lbl_state_title.configure(text="Ouvindo você... 🎤", text_color=self.config.cor_acordado)
            self.btn_toggle_standby.configure(text="Colocar em Standby 💤", fg_color=self.config.cor_standby, hover_color=hover_standby)
        elif state == AppState.THINKING:
            self.lbl_state_title.configure(text="Processando no agy... 🧠", text_color="#f59e0b")
            self.btn_toggle_standby.configure(text="Colocar em Standby 💤", fg_color=self.config.cor_standby, hover_color=hover_standby)
        elif state == AppState.WAITING_PERMISSION:
            self.lbl_state_title.configure(text="Aguardando Autorização ⚠️", text_color="#fbbf24")
            self.btn_toggle_standby.configure(text="Aguardando Autorização ⚠️", fg_color="#d97706", hover_color="#b45309")
        elif state == AppState.SPEAKING:
            self.lbl_state_title.configure(text="Falando resposta... 🔊", text_color="#10b981")
            self.btn_toggle_standby.configure(text="Colocar em Standby 💤", fg_color=self.config.cor_standby, hover_color=hover_standby)

    def alternar_modo_configuracoes(self):
        self.em_modo_configuracoes = not self.em_modo_configuracoes
        if self.em_modo_configuracoes:
            self.frame_orb_view.pack_forget()
            self.settings_view.pack(fill="both", expand=True)
            self.settings_view.atualizar_cores(self.config.cor_acordado, self.config.cor_standby)
        else:
            self.settings_view.pack_forget()
            self.frame_orb_view.pack(fill="both", expand=True)

    def _ao_trocar_voz(self, escolha: str):
        nova_voz = VOZES_DISPONIVEIS.get(escolha, "pt-BR-AntonioNeural")
        self.controller.trocar_voz(nova_voz)
        self.config.tipo_de_voz = escolha
        ConfigManager.salvar(self.config)
        self.chat_feed.adicionar_mensagem("system", f"🔊 Voz alterada para: {escolha}")

    def _ao_mudar_whisper(self, escolha: str):
        modelo_id = MODELOS_WHISPER_DISPONIVEIS.get(escolha, "base")
        self.config.modelo_whisper = escolha
        ConfigManager.salvar(self.config)
        threading.Thread(target=self.controller.trocar_modelo_whisper, args=(modelo_id,), daemon=True).start()

    def _ao_mudar_opacidade(self, valor: float):
        self.config.transparencia = round(valor, 2)
        self.attributes('-alpha', self.config.transparencia)
        ConfigManager.salvar(self.config)

    def _ao_mudar_cor(self, modo: str, hex_code: str):
        if modo == "acordado":
            self.config.cor_acordado = hex_code
            self.chat_feed.adicionar_mensagem("system", f"🎨 Cor Acordado alterada para: {hex_code.upper()}")
        else:
            self.config.cor_standby = hex_code
            self.chat_feed.adicionar_mensagem("system", f"🎨 Cor Standby alterada para: {hex_code.upper()}")

        ConfigManager.salvar(self.config)
        self.orb_canvas.set_colors(self.config.cor_acordado, self.config.cor_standby)
        self._atualizar_visual_estado(self.current_state)
        self.tray.atualizar_cor(self.config.cor_acordado if self.controller.em_conversa else self.config.cor_standby)

    def _ao_mudar_topmost(self, valor: bool):
        self.config.fixar_no_topo = valor
        self.attributes('-topmost', valor)
        ConfigManager.salvar(self.config)

    def _ao_alternar_mudo(self):
        mutado = self.controller.alternar_mudo()
        if mutado:
            self.btn_mute.configure(text="Desmutar Microfone", fg_color="#ef4444", hover_color="#dc2626")
            self.chat_feed.adicionar_mensagem("system", "🔇 Microfone mutado.")
        else:
            self.btn_mute.configure(text="Mutar Microfone", fg_color="#334155", hover_color="#475569")
            self.chat_feed.adicionar_mensagem("system", "🎙️ Microfone reativado.")

    def _alternar_painel_transcricao(self):
        self.config.painel_transcricao_aberto = not self.config.painel_transcricao_aberto
        ConfigManager.salvar(self.config)

        if self.config.painel_transcricao_aberto:
            self.chat_feed.grid(row=0, column=1, padx=(0, 16), pady=16, sticky="nsew")
            self.grid_columnconfigure(1, weight=6)
            self.minsize(850, 560)
            self.geometry("980x640")
            self.btn_toggle_feed.configure(text="💬 Ocultar Transcrição", fg_color="#334155", hover_color="#475569")
        else:
            self.chat_feed.grid_remove()
            self.grid_columnconfigure(1, weight=0)
            self.minsize(380, 560)
            self.geometry("400x620")
            self.btn_toggle_feed.configure(text="💬 Mostrar Transcrição", fg_color="#0284c7", hover_color="#0369a1")

    def minimizar_para_segundo_plano(self):
        self.withdraw()
        self.chat_feed.adicionar_mensagem("system", "🔕 Janela oculta em 2º plano. Use o ícone na bandeja ou diga 'AGY'!")

    def restaurar_janela(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def encerrar_definitivo(self):
        print("🛑 Encerrando AGY Voice Hub definitivamente...")
        self.controller.executando = False
        self.tray.parar()
        pygame.mixer.quit()
        self.destroy()
        sys.exit(0)

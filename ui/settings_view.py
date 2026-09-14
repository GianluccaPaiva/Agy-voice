from typing import Callable
import customtkinter as ctk
from config.settings import MODELOS_WHISPER_DISPONIVEIS
from config.manager import AppConfig
from ui.color_wheel import ColorWheelWidget

class SettingsView(ctk.CTkFrame):
    """Componente de visualização em tela cheia do menu de configurações inline."""

    def __init__(
        self,
        master,
        config: AppConfig,
        on_voltar: Callable[[], None],
        on_opacity_changed: Callable[[float], None],
        on_color_changed: Callable[[str, str], None],
        on_whisper_changed: Callable[[str], None],
        on_topmost_changed: Callable[[bool], None],
        on_exit_app: Callable[[], None],
        **kwargs
    ):
        defaults = {"fg_color": "transparent"}
        defaults.update(kwargs)
        super().__init__(master, **defaults)

        self.config = config
        self.on_voltar = on_voltar
        self.on_opacity_changed = on_opacity_changed
        self.on_color_changed = on_color_changed
        self.on_whisper_changed = on_whisper_changed
        self.on_topmost_changed = on_topmost_changed
        self.on_exit_app = on_exit_app

        self._criar_layout()

    def _criar_layout(self):
        # Header
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.pack(fill="x", padx=16, pady=(16, 6))

        self.btn_voltar = ctk.CTkButton(
            self.frame_header,
            text="← Voltar",
            width=70,
            height=30,
            command=self.on_voltar,
            fg_color="#1e293b",
            hover_color="#334155",
            corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_voltar.pack(side="left")

        self.lbl_title = ctk.CTkLabel(
            self.frame_header,
            text="Configurações Fixas",
            font=ctk.CTkFont(family="Plus Jakarta Sans", size=17, weight="bold"),
            text_color="#f8fafc"
        )
        self.lbl_title.pack(side="left", padx=10)

        # Scroll Box
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        # 1. Card Opacidade
        self.card_opacidade = ctk.CTkFrame(self.scroll, fg_color="#1e293b", corner_radius=14)
        self.card_opacidade.pack(fill="x", pady=4)

        self.lbl_transp = ctk.CTkLabel(
            self.card_opacidade,
            text=f"Opacidade da Janela: {int(self.config.transparencia * 100)}%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1"
        )
        self.lbl_transp.pack(pady=(8, 2), padx=12, anchor="w")

        def _on_slider(val):
            v = float(val)
            self.lbl_transp.configure(text=f"Opacidade da Janela: {int(v * 100)}%")
            self.on_opacity_changed(v)

        self.slider = ctk.CTkSlider(
            self.card_opacidade,
            from_=0.35,
            to=1.0,
            number_of_steps=65,
            command=_on_slider,
            button_color="#06b6d4",
            progress_color="#0284c7"
        )
        self.slider.set(self.config.transparencia)
        self.slider.pack(fill="x", padx=12, pady=(2, 10))

        # 2. Card Círculo de Cores
        self.wheel_widget = ColorWheelWidget(
            self.scroll,
            cor_acordado_inicial=self.config.cor_acordado,
            cor_standby_inicial=self.config.cor_standby,
            on_color_changed=self.on_color_changed
        )
        self.wheel_widget.pack(fill="x", pady=4)

        # 3. Card Qualidade Whisper STT
        self.card_whisper = ctk.CTkFrame(self.scroll, fg_color="#1e293b", corner_radius=14)
        self.card_whisper.pack(fill="x", pady=4)

        self.lbl_whisper = ctk.CTkLabel(
            self.card_whisper,
            text="Qualidade da Transcrição (Whisper STT):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1"
        )
        self.lbl_whisper.pack(pady=(8, 4), padx=12, anchor="w")

        self.combo_whisper = ctk.CTkComboBox(
            self.card_whisper,
            values=list(MODELOS_WHISPER_DISPONIVEIS.keys()),
            command=self.on_whisper_changed,
            fg_color="#0f172a",
            button_color="#0284c7",
            border_color="#334155",
            dropdown_fg_color="#0f172a"
        )
        self.combo_whisper.set(self.config.modelo_whisper)
        self.combo_whisper.pack(fill="x", padx=12, pady=(0, 4))

        self.lbl_whisper_info = ctk.CTkLabel(
            self.card_whisper,
            text="💡 'Small' e 'Turbo' aumentam a precisão em termos técnicos.",
            font=ctk.CTkFont(size=10),
            text_color="#94a3b8"
        )
        self.lbl_whisper_info.pack(padx=12, pady=(0, 8), anchor="w")

        # 4. Card Opções de Janela
        self.card_opcoes = ctk.CTkFrame(self.scroll, fg_color="#1e293b", corner_radius=14)
        self.card_opcoes.pack(fill="x", pady=4)

        self.switch_topmost = ctk.CTkSwitch(
            self.card_opcoes,
            text="Fixar sempre no topo da tela",
            command=lambda: self.on_topmost_changed(bool(self.switch_topmost.get())),
            font=ctk.CTkFont(size=12),
            progress_color="#3b82f6"
        )
        if self.config.fixar_no_topo:
            self.switch_topmost.select()
        self.switch_topmost.pack(padx=12, pady=(10, 8), anchor="w")

        self.lbl_info = ctk.CTkLabel(
            self.card_opcoes,
            text="ℹ Ao clicar no 'X', o app fica ativo em 2º plano.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_info.pack(padx=12, pady=(0, 10), anchor="w")

        # 5. Botão Encerramento
        self.btn_exit = ctk.CTkButton(
            self.scroll,
            text="🛑 Encerrar Aplicativo Definitivamente",
            command=self.on_exit_app,
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=12,
            height=36
        )
        self.btn_exit.pack(fill="x", pady=(8, 10))

    def atualizar_cores(self, cor_acordado: str, cor_standby: str):
        self.wheel_widget.cor_acordado = cor_acordado
        self.wheel_widget.cor_standby = cor_standby
        self.wheel_widget.atualizar_preview()

import customtkinter as ctk
from typing import Callable, Optional

class ChatFeedComponent(ctk.CTkFrame):
    """Componente do painel direito com visualização de transcrições, histórico e cards de autorização."""
    
    def __init__(self, master, on_permission_response: Optional[Callable[[str, bool], None]] = None, **kwargs):
        defaults = {
            "fg_color": "#0f172a",
            "corner_radius": 20,
            "border_width": 1,
            "border_color": "#1e293b"
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)
        
        self.on_permission_response = on_permission_response
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._criar_layout()

    def _criar_layout(self):
        # Top Bar do Feed
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")

        self.lbl_title = ctk.CTkLabel(
            self.frame_top,
            text="Transcrições & Diálogo em Tempo Real",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e2e8f0"
        )
        self.lbl_title.pack(side="left")

        self.btn_limpar = ctk.CTkButton(
            self.frame_top,
            text="Limpar",
            width=60,
            height=24,
            command=self.limpar,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=11)
        )
        self.btn_limpar.pack(side="right")

        # Chat Textbox
        self.txt_feed = ctk.CTkTextbox(
            self,
            fg_color="#090d16",
            text_color="#f8fafc",
            corner_radius=14,
            font=ctk.CTkFont(family="Plus Jakarta Sans", size=13),
            wrap="word",
            border_width=1,
            border_color="#1e293b"
        )
        self.txt_feed.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        self.txt_feed.configure(state="disabled")

        # Frame de Card de Permissão Interativo (Oculto por padrão)
        self.frame_card_perm = ctk.CTkFrame(
            self,
            fg_color="#1e1b4b",
            corner_radius=14,
            border_width=2,
            border_color="#f59e0b"
        )
        self._criar_conteudo_card_perm()

        # Dicas do Rodapé
        self.lbl_hint = ctk.CTkLabel(
            self,
            text="💡 Diga 'Sim/Yes' ou 'Não' para autorizar • Fale por cima para interromper",
            font=ctk.CTkFont(size=11),
            text_color="#64748b"
        )
        self.lbl_hint.grid(row=3, column=0, padx=16, pady=(4, 12), sticky="w")

    def _criar_conteudo_card_perm(self):
        self.lbl_perm_header = ctk.CTkLabel(
            self.frame_card_perm,
            text="⚠️ Solicitação de Autorização do AGY",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#fbbf24"
        )
        self.lbl_perm_header.pack(anchor="w", padx=14, pady=(10, 2))

        self.lbl_perm_desc = ctk.CTkLabel(
            self.frame_card_perm,
            text="O AGY solicita permissão para executar uma ação:",
            font=ctk.CTkFont(size=12),
            text_color="#e2e8f0"
        )
        self.lbl_perm_desc.pack(anchor="w", padx=14, pady=(0, 4))

        self.txt_perm_detalhe = ctk.CTkLabel(
            self.frame_card_perm,
            text="",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#38bdf8",
            wraplength=450,
            justify="left"
        )
        self.txt_perm_detalhe.pack(anchor="w", padx=14, pady=(0, 8))

        # Botões de Ação
        self.frame_botoes_perm = ctk.CTkFrame(self.frame_card_perm, fg_color="transparent")
        self.frame_botoes_perm.pack(fill="x", padx=14, pady=(0, 10))

        self.btn_aceitar = ctk.CTkButton(
            self.frame_botoes_perm,
            text="✔ Aceitar (Yes)",
            fg_color="#10b981",
            hover_color="#059669",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._clique_aceitar
        )
        self.btn_aceitar.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_recusar = ctk.CTkButton(
            self.frame_botoes_perm,
            text="✖ Recusar (No)",
            fg_color="#ef4444",
            hover_color="#dc2626",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._clique_recusar
        )
        self.btn_recusar.pack(side="right", fill="x", expand=True, padx=(6, 0))

        self.current_req_id = ""

    def mostrar_solicitacao_permissao(self, req_id: str, description: str, details: str):
        self.current_req_id = req_id
        self.lbl_perm_desc.configure(text=f"Ação: {description}")
        self.txt_perm_detalhe.configure(text=details if details else "(Sem parâmetros adicionais)")
        
        self.btn_aceitar.configure(state="normal", text="✔ Aceitar (Yes)")
        self.btn_recusar.configure(state="normal", text="✖ Recusar (No)")
        
        self.frame_card_perm.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="ew")

    def esconder_solicitacao_permissao(self):
        self.frame_card_perm.grid_forget()

    def _clique_aceitar(self):
        self.btn_aceitar.configure(state="disabled", text="✔ Autorizado!")
        self.btn_recusar.configure(state="disabled")
        if self.on_permission_response and self.current_req_id:
            self.on_permission_response(self.current_req_id, True)

    def _clique_recusar(self):
        self.btn_recusar.configure(state="disabled", text="✖ Recusado!")
        self.btn_aceitar.configure(state="disabled")
        if self.on_permission_response and self.current_req_id:
            self.on_permission_response(self.current_req_id, False)

    def adicionar_mensagem(self, remetente: str, mensagem: str):
        self.txt_feed.configure(state="normal")
        if remetente == "user":
            self.txt_feed.insert("end", f"\n👤 Você:\n{mensagem}\n")
        elif remetente == "agy":
            self.txt_feed.insert("end", f"\n🤖 AGY:\n{mensagem}\n")
        else:
            self.txt_feed.insert("end", f"\n⚙️ {mensagem}\n")

        self.txt_feed.see("end")
        self.txt_feed.configure(state="disabled")

    def limpar(self):
        self.txt_feed.configure(state="normal")
        self.txt_feed.delete("1.0", "end")
        self.txt_feed.configure(state="disabled")

import customtkinter as ctk

class ChatFeedComponent(ctk.CTkFrame):
    """Componente do painel direito com visualização de transcrições e histórico de diálogo."""
    
    def __init__(self, master, **kwargs):
        defaults = {
            "fg_color": "#0f172a",
            "corner_radius": 20,
            "border_width": 1,
            "border_color": "#1e293b"
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)
        
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

        # Dicas do Rodapé
        self.lbl_hint = ctk.CTkLabel(
            self,
            text="💡 Diga 'sair da conversa' para pausar ou 'AGY' para acordar • Fale por cima para interromper",
            font=ctk.CTkFont(size=11),
            text_color="#64748b"
        )
        self.lbl_hint.grid(row=2, column=0, padx=16, pady=(4, 12), sticky="w")

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

import math
import colorsys
from typing import Callable, Tuple, Optional
from tkinter import colorchooser
import customtkinter as ctk
from PIL import Image, ImageTk
from config.settings import PRESETS_CORES_CIRCULO

def gerar_imagem_circulo_cores(diametro: int = 140) -> Image.Image:
    """Gera uma imagem RGBA de alta qualidade com círculo cromático HSV suave e borda antialiased."""
    img = Image.new("RGBA", (diametro, diametro), (0, 0, 0, 0))
    pixels = img.load()
    cx = diametro / 2.0
    cy = diametro / 2.0
    r_max = (diametro - 6) / 2.0

    for y in range(diametro):
        for x in range(diametro):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= r_max:
                angle = (math.atan2(dy, dx) + math.pi) / (2 * math.pi)
                sat = min(1.0, dist / r_max)
                r, g, b = colorsys.hsv_to_rgb(angle, sat, 1.0)
                
                alpha = 255
                if dist > r_max - 1.5:
                    alpha = max(0, min(255, int(255 * (r_max - dist) / 1.5)))
                    
                pixels[x, y] = (int(r * 255), int(g * 255), int(b * 255), alpha)
    return img

def calcular_cor_de_xy(x: float, y: float, cx: float, cy: float, r_max: float) -> Tuple[str, float, float]:
    dx = x - cx
    dy = y - cy
    dist = math.sqrt(dx * dx + dy * dy)
    
    if dist > r_max:
        if dist > 0:
            dx = (dx / dist) * r_max
            dy = (dy / dist) * r_max
        dist = r_max

    angle = (math.atan2(dy, dx) + math.pi) / (2 * math.pi)
    sat = max(0.0, min(1.0, dist / r_max))
    r, g, b = colorsys.hsv_to_rgb(angle, sat, 1.0)
    hex_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    return hex_color, cx + dx, cy + dy

def calcular_xy_de_hex(hex_str: str, cx: float, cy: float, r_max: float) -> Tuple[float, float]:
    try:
        hex_clean = hex_str.lstrip('#')
        if len(hex_clean) == 6:
            r = int(hex_clean[0:2], 16) / 255.0
            g = int(hex_clean[2:4], 16) / 255.0
            b = int(hex_clean[4:6], 16) / 255.0
            h, s, _ = colorsys.rgb_to_hsv(r, g, b)
            angle = h * 2 * math.pi - math.pi
            dist = s * r_max
            return cx + dist * math.cos(angle), cy + dist * math.sin(angle)
    except Exception:
        pass
    return cx, cy

def ajustar_saturacao_cor(hex_str: str, fator_saturacao: float = 0.82, fator_brilho: float = 1.1) -> str:
    """Ajusta suavemente a saturação e brilho para o hover dinâmico dos botões."""
    try:
        hex_clean = hex_str.lstrip('#')
        if len(hex_clean) == 6:
            r = int(hex_clean[0:2], 16) / 255.0
            g = int(hex_clean[2:4], 16) / 255.0
            b = int(hex_clean[4:6], 16) / 255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            
            if s > 0.2:
                nova_s = max(0.0, min(1.0, s * fator_saturacao))
                nova_v = max(0.0, min(1.0, v * fator_brilho))
            else:
                nova_s = s
                nova_v = max(0.0, min(1.0, v * 0.85 if v > 0.7 else v * 1.2))
                
            nr, ng, nb = colorsys.hsv_to_rgb(h, nova_s, nova_v)
            return f"#{int(nr*255):02x}{int(ng*255):02x}{int(nb*255):02x}"
    except Exception:
        pass
    return hex_str

class ColorWheelWidget(ctk.CTkFrame):
    """Componente visual de Círculo de Cores interativo."""
    
    def __init__(
        self,
        master,
        cor_acordado_inicial: str,
        cor_standby_inicial: str,
        on_color_changed: Callable[[str, str], None], # (modo: 'acordado'|'standby', hex_code)
        **kwargs
    ):
        super().__init__(master, fg_color="#1e293b", corner_radius=14, **kwargs)
        self.cor_acordado = cor_acordado_inicial
        self.cor_standby = cor_standby_inicial
        self.on_color_changed = on_color_changed

        self.wheel_diametro = 140
        self.wheel_cx = self.wheel_diametro / 2.0
        self.wheel_cy = self.wheel_diametro / 2.0
        self.wheel_r_max = (self.wheel_diametro - 6) / 2.0

        self.pil_img = gerar_imagem_circulo_cores(self.wheel_diametro)
        self.photo_img = ImageTk.PhotoImage(self.pil_img)

        self._criar_layout()
        self.redesenhar()

    def _criar_layout(self):
        self.lbl_title = ctk.CTkLabel(
            self,
            text="🎨 Círculo de Cores do Orb:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1"
        )
        self.lbl_title.pack(pady=(8, 4), padx=12, anchor="w")

        self.seg_modo = ctk.CTkSegmentedButton(
            self,
            values=["⚡ Acordado", "💤 Standby"],
            command=lambda _: self.atualizar_preview(),
            selected_color="#0284c7",
            selected_hover_color="#0369a1",
            unselected_color="#0f172a",
            unselected_hover_color="#334155"
        )
        self.seg_modo.set("⚡ Acordado")
        self.seg_modo.pack(fill="x", padx=12, pady=(2, 6))

        self.canvas_wheel = ctk.CTkCanvas(
            self,
            width=self.wheel_diametro,
            height=self.wheel_diametro,
            bg="#1e293b",
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas_wheel.pack(pady=4)
        self.canvas_wheel.bind("<Button-1>", self._ao_interagir_wheel)
        self.canvas_wheel.bind("<B1-Motion>", self._ao_interagir_wheel)

        # Preview e Botão Mais Cores
        self.frame_preview = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=8)
        self.frame_preview.pack(fill="x", padx=12, pady=(4, 6))

        self.swatch = ctk.CTkLabel(
            self.frame_preview,
            text="",
            width=20,
            height=20,
            fg_color=self.cor_acordado,
            corner_radius=10
        )
        self.swatch.pack(side="left", padx=(8, 6), pady=6)

        self.lbl_hex = ctk.CTkLabel(
            self.frame_preview,
            text=f"Acordado: {self.cor_acordado.upper()}",
            font=ctk.CTkFont(family="JetBrains Mono", size=11, weight="bold"),
            text_color="#e2e8f0"
        )
        self.lbl_hex.pack(side="left", padx=4, pady=6)

        self.btn_dialog = ctk.CTkButton(
            self.frame_preview,
            text="Mais Cores",
            width=70,
            height=24,
            command=self._abrir_dialogo_sistema,
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=6,
            font=ctk.CTkFont(size=10)
        )
        self.btn_dialog.pack(side="right", padx=6, pady=6)

        # Paleta de Mini Chips Rápidos
        self.frame_presets = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_presets.pack(pady=(0, 8))

        for hex_code, _ in PRESETS_CORES_CIRCULO:
            btn = ctk.CTkButton(
                self.frame_presets,
                text="",
                width=18,
                height=18,
                fg_color=hex_code,
                hover_color=hex_code,
                corner_radius=9,
                command=lambda c=hex_code: self._aplicar_cor(c)
            )
            btn.pack(side="left", padx=2)

    def _ao_interagir_wheel(self, event):
        hex_color, _, _ = calcular_cor_de_xy(event.x, event.y, self.wheel_cx, self.wheel_cy, self.wheel_r_max)
        self._aplicar_cor(hex_color)

    def _abrir_dialogo_sistema(self):
        modo_atual = "acordado" if "Acordado" in self.seg_modo.get() else "standby"
        cor_base = self.cor_acordado if modo_atual == "acordado" else self.cor_standby
        escolha = colorchooser.askcolor(initialcolor=cor_base, title="Escolha uma cor para o Orb")
        if escolha and escolha[1]:
            self._aplicar_cor(escolha[1])

    def _aplicar_cor(self, hex_color: str):
        modo_atual = "acordado" if "Acordado" in self.seg_modo.get() else "standby"
        if modo_atual == "acordado":
            self.cor_acordado = hex_color
        else:
            self.cor_standby = hex_color

        self.atualizar_preview()
        self.on_color_changed(modo_atual, hex_color)

    def redesenhar(self):
        self.canvas_wheel.delete("all")
        self.canvas_wheel.create_image(self.wheel_cx, self.wheel_cy, image=self.photo_img)

        modo = "acordado" if "Acordado" in self.seg_modo.get() else "standby"
        cor_atual = self.cor_acordado if modo == "acordado" else self.cor_standby

        cur_x, cur_y = calcular_xy_de_hex(cor_atual, self.wheel_cx, self.wheel_cy, self.wheel_r_max)

        self.canvas_wheel.create_oval(cur_x - 7, cur_y - 7, cur_x + 7, cur_y + 7, outline="#000000", width=3)
        self.canvas_wheel.create_oval(cur_x - 6, cur_y - 6, cur_x + 6, cur_y + 6, outline="#ffffff", width=2, fill=cor_atual)

    def atualizar_preview(self):
        modo = "acordado" if "Acordado" in self.seg_modo.get() else "standby"
        cor_atual = self.cor_acordado if modo == "acordado" else self.cor_standby
        texto = f"{'Acordado' if modo == 'acordado' else 'Standby'}: {cor_atual.upper()}"

        self.swatch.configure(fg_color=cor_atual)
        self.lbl_hex.configure(text=texto)
        self.redesenhar()

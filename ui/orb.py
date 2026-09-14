import time
import math
import customtkinter as ctk
from core.states import AppState

class GlowingOrbCanvas(ctk.CTkCanvas):
    """Componente Canvas com animação do Glowing Energy Orb reagente ao volume e estado."""
    
    def __init__(self, master, cor_acordado: str, cor_standby: str, **kwargs):
        defaults = {
            "width": 230,
            "height": 230,
            "bg": "#0f172a",
            "highlightthickness": 0
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)
        
        self.cor_acordado = cor_acordado
        self.cor_standby = cor_standby
        self.current_state = AppState.LISTENING
        self.current_volume = 0.0
        self.angle = 0.0
        self.pausado = False

    def set_state(self, state: AppState):
        self.current_state = state

    def set_volume(self, volume: float):
        self.current_volume = volume

    def set_colors(self, cor_acordado: str, cor_standby: str):
        self.cor_acordado = cor_acordado
        self.cor_standby = cor_standby

    def animar(self):
        if not self.pausado:
            self.delete("all")
            cx, cy = 115, 115
            self.angle += 0.05
            t = time.time()

            if self.current_state == AppState.STANDBY:
                base_r = 45 + math.sin(t * 2) * 3
                cor_centro = self.cor_standby
                cor_anel = "#ffffff"
            elif self.current_state == AppState.LISTENING:
                vol_boost = min(25, self.current_volume * 350)
                base_r = 55 + math.sin(t * 5) * 5 + vol_boost
                cor_centro = self.cor_acordado
                cor_anel = "#ffffff"
            elif self.current_state == AppState.THINKING:
                base_r = 52 + math.sin(t * 8) * 5
                cor_centro = "#f59e0b"
                cor_anel = "#fbbf24"
            elif self.current_state == AppState.WAITING_PERMISSION:
                vol_boost = min(20, self.current_volume * 300)
                base_r = 56 + math.sin(t * 10) * 7 + vol_boost
                cor_centro = "#f59e0b"
                cor_anel = "#ef4444"
            else:  # SPEAKING
                base_r = 60 + math.sin(t * 6) * 9
                cor_centro = "#10b981"
                cor_anel = "#34d399"


            # Círculo externo difuso
            self.create_oval(
                cx - base_r * 1.3, cy - base_r * 1.3,
                cx + base_r * 1.3, cy + base_r * 1.3,
                fill="", outline=cor_centro, width=1
            )

            # Núcleo brilhante
            self.create_oval(
                cx - base_r, cy - base_r,
                cx + base_r, cy + base_r,
                fill=cor_centro, outline=cor_anel, width=2
            )

            # Partículas orbitais
            num_particulas = 12
            for i in range(num_particulas):
                a = self.angle + (i / num_particulas) * math.pi * 2
                raio_orbita = base_r * 1.2 + math.sin(a * 3 + t * 4) * 4
                px = cx + math.cos(a) * raio_orbita
                py = cy + math.sin(a) * raio_orbita
                self.create_oval(px - 2.5, py - 2.5, px + 2.5, py + 2.5, fill="#ffffff", outline="")

        self.after(33, self.animar)

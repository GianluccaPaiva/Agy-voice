import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw
import pystray

class SystemTrayManager:
    """Gerenciador do ícone e menu de contexto da bandeja do sistema (System Tray)."""

    def __init__(
        self,
        on_restaurar: Callable[[], None],
        on_alternar_standby: Callable[[], None],
        on_encerrar: Callable[[], None],
        cor_inicial: str = "#06b6d4"
    ):
        self.on_restaurar = on_restaurar
        self.on_alternar_standby = on_alternar_standby
        self.on_encerrar = on_encerrar
        self.cor_atual = cor_inicial
        self._tray_icon: Optional[pystray.Icon] = None

    def _criar_imagem_icone(self, cor: str) -> Image.Image:
        img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((8, 8, 56, 56), fill=cor, outline="#ffffff", width=2)
        draw.ellipse((22, 22, 42, 42), fill="#0f172a")
        return img

    def iniciar(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Abrir AGY Voice Hub", lambda: self.on_restaurar(), default=True),
            pystray.MenuItem("Alternar Standby / Ativo", lambda: self.on_alternar_standby()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🛑 Encerrar Definitivamente", lambda: self.on_encerrar())
        )
        self._tray_icon = pystray.Icon("AGY Voice Hub", self._criar_imagem_icone(self.cor_atual), "AGY Voice Hub", menu)
        tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
        tray_thread.start()

    def atualizar_cor(self, cor: str) -> None:
        self.cor_atual = cor
        if self._tray_icon:
            try:
                self._tray_icon.icon = self._criar_imagem_icone(cor)
            except Exception:
                pass

    def parar(self) -> None:
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass

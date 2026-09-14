import io
import asyncio
from typing import Tuple, Optional, List
import numpy as np
import pygame
import sounddevice as sd
import edge_tts

class EdgeTTSEngine:
    """
    Motor de síntese de voz (Text-to-Speech) 100% em memória RAM via edge-tts e Pygame.
    Possui suporte em tempo real a interrupção de fala (Barge-in).
    """
    def __init__(self, voz_inicial: str = "pt-BR-AntonioNeural"):
        self.voz_atual = voz_inicial
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    async def falar(
        self,
        texto: str,
        permitir_interrupcao: bool = True,
        threshold_interrupcao: float = 0.03
    ) -> Tuple[bool, Optional[List[np.ndarray]]]:
        if not texto or not texto.strip():
            return False, None

        try:
            comunicador = edge_tts.Communicate(texto, self.voz_atual)
            audio_data = bytearray()
            async for chunk in comunicador.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])

            if not audio_data:
                return False, None

            audio_buffer = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()

            interrompido = False
            chunks_voz: List[np.ndarray] = []

            if permitir_interrupcao:
                chunk_check = int(16000 * 0.1)
                with sd.InputStream(samplerate=16000, channels=1, dtype='float32', blocksize=chunk_check) as mic_stream:
                    while pygame.mixer.music.get_busy():
                        data, _ = mic_stream.read(chunk_check)
                        vol = float(np.sqrt(np.mean(data ** 2)))
                        if vol > threshold_interrupcao:
                            pygame.mixer.music.stop()
                            interrompido = True
                            chunks_voz.append(data.copy())
                            break
                        await asyncio.sleep(0.05)
            else:
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.1)

            pygame.mixer.music.unload()
            return interrompido, (chunks_voz if interrompido else None)

        except Exception as e:
            print(f"⚠️ Erro ao sintetizar/tocar TTS: {e}")
            return False, None

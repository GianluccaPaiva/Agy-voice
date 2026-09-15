import io
import re
import asyncio
from typing import Tuple, Optional, List
import numpy as np
import pygame
import sounddevice as sd
import edge_tts

class EdgeTTSEngine:
    """
    Motor de síntese de voz (Text-to-Speech) 100% em memória RAM via edge-tts e Pygame.
    Possui pipeline dinâmico por sentenças com suporte em tempo real a interrupção de fala (Barge-in).
    """
    def __init__(self, voz_inicial: str = "pt-BR-AntonioNeural"):
        self.voz_atual = voz_inicial
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    @staticmethod
    def _dividir_em_sentencas(texto: str) -> List[str]:
        """Divide o texto em frases menores para acelerar o Time-To-First-Audio (TTFA)."""
        if not texto or not texto.strip():
            return []

        texto_limpo = texto.strip()
        # Divide por pontuações fortes (. ? ! : \n) seguidas de espaço ou fim de linha
        padrao = r'(?<=[.!?:\n])\s+'
        partes = re.split(padrao, texto_limpo)

        sentencas: List[str] = []
        for parte in partes:
            p = parte.strip()
            if not p:
                continue
            # Se for muito longa (> 180 caracteres sem pontuação), divide por vírgulas ou ponto-e-vírgula
            if len(p) > 180:
                subpartes = re.split(r'(?<=[,;])\s+', p)
                sentencas.extend([sp.strip() for sp in subpartes if sp.strip()])
            else:
                sentencas.append(p)

        return sentencas if sentencas else [texto_limpo]

    async def _sintetizar_para_buffer(self, texto_sentenca: str) -> Optional[io.BytesIO]:
        """Sintetiza uma única sentença na RAM via edge-tts."""
        try:
            comunicador = edge_tts.Communicate(texto_sentenca, self.voz_atual)
            audio_data = bytearray()
            async for chunk in comunicador.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])

            if audio_data:
                return io.BytesIO(audio_data)
            return None
        except Exception as e:
            print(f"⚠️ Erro ao sintetizar sentença TTS ('{texto_sentenca[:30]}...'): {e}")
            return None

    async def falar(
        self,
        texto: str,
        permitir_interrupcao: bool = True,
        threshold_interrupcao: float = 0.018
    ) -> Tuple[bool, Optional[List[np.ndarray]]]:
        """
        Sintetiza e reproduz o texto frase por frase em pipeline (Producer-Consumer).
        Inicia a reprodução da 1ª frase enquanto as frases seguintes são sintetizadas em background.
        Suporta interrupção imediata por voz (Barge-in) com sensibilidade calibrada.
        """
        if not texto or not texto.strip():
            return False, None

        sentencas = self._dividir_em_sentencas(texto)
        if not sentencas:
            return False, None

        fila_audio: asyncio.Queue[Optional[io.BytesIO]] = asyncio.Queue(maxsize=10)
        tarefa_produtor: Optional[asyncio.Task] = None
        interrompido = False
        chunks_voz: List[np.ndarray] = []

        async def produtor():
            try:
                for sentenca in sentencas:
                    buf = await self._sintetizar_para_buffer(sentenca)
                    if buf is not None:
                        await fila_audio.put(buf)
            except asyncio.CancelledError:
                pass
            except Exception as ex:
                print(f"⚠️ Erro no produtor dinâmico de TTS: {ex}")
            finally:
                await fila_audio.put(None)  # Sinal de término da fila

        try:
            tarefa_produtor = asyncio.create_task(produtor())

            if permitir_interrupcao:
                chunk_check = int(16000 * 0.1)  # Chunks de 100ms
                with sd.InputStream(samplerate=16000, channels=1, dtype='float32', blocksize=chunk_check) as mic_stream:
                    while True:
                        audio_buffer = await fila_audio.get()
                        if audio_buffer is None:
                            break

                        pygame.mixer.music.load(audio_buffer)
                        pygame.mixer.music.play()

                        while pygame.mixer.music.get_busy():
                            data, _ = await asyncio.to_thread(mic_stream.read, chunk_check)
                            vol = float(np.sqrt(np.mean(data ** 2)))
                            if vol > threshold_interrupcao:
                                pygame.mixer.music.stop()
                                interrompido = True
                                chunks_voz.append(data.copy())
                                break

                        pygame.mixer.music.unload()

                        if interrompido:
                            break
            else:
                while True:
                    audio_buffer = await fila_audio.get()
                    if audio_buffer is None:
                        break

                    pygame.mixer.music.load(audio_buffer)
                    pygame.mixer.music.play()

                    while pygame.mixer.music.get_busy():
                        await asyncio.sleep(0.08)

                    pygame.mixer.music.unload()

            return interrompido, (chunks_voz if interrompido else None)

        except Exception as e:
            print(f"⚠️ Erro na reprodução de TTS: {e}")
            return False, None
        finally:
            if tarefa_produtor and not tarefa_produtor.done():
                tarefa_produtor.cancel()
                try:
                    await tarefa_produtor
                except asyncio.CancelledError:
                    pass



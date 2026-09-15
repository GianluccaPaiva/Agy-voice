import io
import re
import asyncio
import threading
from typing import Tuple, Optional, List, Callable
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

    async def falar_fila_sentencas(
        self,
        fila_sentencas: asyncio.Queue[Optional[str]],
        permitir_interrupcao: bool = True,
        threshold_interrupcao: float = 0.016,
        volume_callback: Optional[Callable[[float], None]] = None,
        is_muted: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Sintetiza e reproduz sentenças conforme chegam da fila em streaming paralelo.
        Monitora microfone em tempo real com interrupção instantânea (Barge-in).
        Garante respeito absoluto ao estado de mudo.
        """
        if is_muted and is_muted():
            permitir_interrupcao = False

        fila_audio: asyncio.Queue[Optional[io.BytesIO]] = asyncio.Queue(maxsize=10)
        tarefa_produtor: Optional[asyncio.Task] = None
        evento_parar_produtor = asyncio.Event()

        async def produtor():
            try:
                while not evento_parar_produtor.is_set():
                    sentenca = await fila_sentencas.get()
                    if sentenca is None or evento_parar_produtor.is_set():
                        break
                    
                    subpartes = self._dividir_em_sentencas(sentenca)
                    for sp in subpartes:
                        if evento_parar_produtor.is_set():
                            break
                        buf = await self._sintetizar_para_buffer(sp)
                        if evento_parar_produtor.is_set():
                            break
                        if buf is not None:
                            await fila_audio.put(buf)
            except asyncio.CancelledError:
                pass
            except Exception as ex:
                print(f"⚠️ Erro no produtor dinâmico de TTS: {ex}")
            finally:
                await fila_audio.put(None)

        if not permitir_interrupcao:
            try:
                tarefa_produtor = asyncio.create_task(produtor())
                while True:
                    audio_buffer = await fila_audio.get()
                    if audio_buffer is None:
                        break
                    pygame.mixer.music.load(audio_buffer)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        await asyncio.sleep(0.05)
                    pygame.mixer.music.unload()
                return False, None
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

        # ----------------------------------------------------
        # MODO COM SUPORTE A INTERRUPÇÃO INSTANTÂNEA (BARGE-IN)
        # ----------------------------------------------------
        chunks_interrupcao: List[np.ndarray] = []
        voz_detectada = threading.Event()
        parar_mic = threading.Event()

        def monitor_microfone():
            taxa = 16000
            chunk_size = int(taxa * 0.08)  # Chunks de 80ms para resposta ultra rápida
            pre_buffer: List[np.ndarray] = []
            max_pre_buffer = 5  # 400ms de buffer pré-gatilho para não perder o início da fala
            gravando_interrupcao = False
            tempo_silencio = 0.0
            tempo_gravado = 0.0

            try:
                with sd.InputStream(samplerate=taxa, channels=1, dtype='float32', blocksize=chunk_size) as mic_stream:
                    while not parar_mic.is_set():
                        if is_muted and is_muted():
                            if volume_callback:
                                volume_callback(0.0)
                            time.sleep(0.1)
                            continue

                        data, _ = mic_stream.read(chunk_size)

                        if is_muted and is_muted():
                            if volume_callback:
                                volume_callback(0.0)
                            continue

                        vol = float(np.sqrt(np.mean(data ** 2)))

                        if volume_callback:
                            volume_callback(vol)

                        if not gravando_interrupcao:
                            pre_buffer.append(data.copy())
                            if len(pre_buffer) > max_pre_buffer:
                                pre_buffer.pop(0)

                            if vol > threshold_interrupcao:
                                pygame.mixer.music.stop()
                                voz_detectada.set()
                                gravando_interrupcao = True
                                chunks_interrupcao.extend(pre_buffer)
                        else:
                            chunks_interrupcao.append(data.copy())
                            tempo_gravado += 0.08
                            if vol < threshold_interrupcao:
                                tempo_silencio += 0.08
                            else:
                                tempo_silencio = 0.0

                            if tempo_silencio >= 0.85 or tempo_gravado >= 25.0:
                                break
            except Exception as ex:
                print(f"⚠️ Erro no monitor de microfone do TTS: {ex}")

        mic_thread = threading.Thread(target=monitor_microfone, daemon=True)
        mic_thread.start()

        try:
            tarefa_produtor = asyncio.create_task(produtor())

            while not voz_detectada.is_set():
                try:
                    audio_buffer = await asyncio.wait_for(fila_audio.get(), timeout=0.08)
                except asyncio.TimeoutError:
                    if voz_detectada.is_set():
                        break
                    if tarefa_produtor.done() and fila_audio.empty():
                        break
                    continue

                if audio_buffer is None or voz_detectada.is_set():
                    break

                pygame.mixer.music.load(audio_buffer)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    if voz_detectada.is_set():
                        pygame.mixer.music.stop()
                        break
                    await asyncio.sleep(0.04)

                pygame.mixer.music.unload()

            if voz_detectada.is_set() and not (is_muted and is_muted()):
                evento_parar_produtor.set()
                if tarefa_produtor and not tarefa_produtor.done():
                    tarefa_produtor.cancel()

                await asyncio.to_thread(mic_thread.join, timeout=10.0)

                if chunks_interrupcao and not (is_muted and is_muted()):
                    audio_final = np.concatenate(chunks_interrupcao, axis=0).flatten().astype(np.float32)
                    return True, audio_final
                return False, None
            else:
                parar_mic.set()
                await asyncio.to_thread(mic_thread.join, timeout=1.0)
                return False, None

        except Exception as e:
            print(f"⚠️ Erro no loop de fala TTS: {e}")
            parar_mic.set()
            return False, None
        finally:
            parar_mic.set()
            evento_parar_produtor.set()
            if tarefa_produtor and not tarefa_produtor.done():
                tarefa_produtor.cancel()
                try:
                    await tarefa_produtor
                except asyncio.CancelledError:
                    pass

    async def falar(
        self,
        texto: str,
        permitir_interrupcao: bool = True,
        threshold_interrupcao: float = 0.016,
        volume_callback: Optional[Callable[[float], None]] = None,
        is_muted: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, Optional[np.ndarray]]:
        """Sintetiza e reproduz um texto completo."""
        if not texto or not texto.strip():
            return False, None

        sentencas = self._dividir_em_sentencas(texto)
        if not sentencas:
            return False, None

        fila: asyncio.Queue[Optional[str]] = asyncio.Queue()
        for s in sentencas:
            fila.put_nowait(s)
        fila.put_nowait(None)

        return await self.falar_fila_sentencas(
            fila_sentencas=fila,
            permitir_interrupcao=permitir_interrupcao,
            threshold_interrupcao=threshold_interrupcao,
            volume_callback=volume_callback,
            is_muted=is_muted
        )



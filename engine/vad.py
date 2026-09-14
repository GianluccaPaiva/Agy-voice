import time
from typing import Optional, List, Callable
import numpy as np
import sounddevice as sd

class AcousticPreFilter:
    """Pré-filtro acústico para descartar ruídos curtos e cliques sem consumir CPU com IA."""

    @staticmethod
    def validar_presenca_voz(audio_array: np.ndarray, taxa: int = 16000) -> bool:
        if audio_array is None or len(audio_array) == 0:
            return False
        # Descarta gravações com menos de 350ms
        if len(audio_array) / taxa < 0.35:
            return False
        # Descarta se amplitude máxima ou RMS for ruído ambiente puro
        pico = float(np.max(np.abs(audio_array)))
        rms = float(np.sqrt(np.mean(audio_array ** 2)))
        if pico < 0.035 or rms < 0.007:
            return False
        return True

class AudioRecorderVAD:
    """
    Gravador de áudio em tempo real baseado em Voice Activity Detection (VAD).
    Opera 100% em memória RAM usando buffers NumPy.
    """
    def __init__(self, volume_callback: Optional[Callable[[float], None]] = None, status_callback: Optional[Callable[[str], None]] = None):
        self.volume_callback = volume_callback
        self.status_callback = status_callback
        self.microfone_mutado = False
        self.interromper = False
        self.executando = True

    def gravar(
        self,
        taxa: int = 16000,
        threshold: float = 0.015,
        silencio_limite: float = 1.2,
        max_duracao: float = 30.0,
        frames_iniciais: Optional[List[np.ndarray]] = None,
        falando_inicial: bool = False
    ) -> Optional[np.ndarray]:
        chunk_size = int(taxa * 0.1)  # Chunks de 100ms
        frames = list(frames_iniciais) if frames_iniciais else []
        pre_buffer: List[np.ndarray] = []
        max_pre_buffer_len = int(0.5 / 0.1)  # 0.5s de buffer para não cortar início
        falando = falando_inicial
        tempo_silencio = 0.0
        tempo_total = len(frames) * 0.1

        with sd.InputStream(samplerate=taxa, channels=1, dtype='float32', blocksize=chunk_size) as stream:
            while self.executando:
                if self.interromper:
                    self.interromper = False
                    return None

                if self.microfone_mutado:
                    time.sleep(0.1)
                    continue

                data, _ = stream.read(chunk_size)
                volume = float(np.sqrt(np.mean(data ** 2)))
                tempo_total += 0.1

                if self.volume_callback:
                    self.volume_callback(volume)

                if not falando:
                    pre_buffer.append(data.copy())
                    if len(pre_buffer) > max_pre_buffer_len:
                        pre_buffer.pop(0)

                    if volume > threshold:
                        falando = True
                        frames.extend(pre_buffer)
                        if self.status_callback:
                            self.status_callback("🎤 Voz detectada! Gravando...")
                else:
                    frames.append(data.copy())
                    if volume < threshold:
                        tempo_silencio += 0.1
                    else:
                        tempo_silencio = 0.0

                    if tempo_silencio >= silencio_limite or tempo_total >= max_duracao:
                        break

        if frames:
            return np.concatenate(frames, axis=0).flatten().astype(np.float32)
        return np.zeros(taxa, dtype=np.float32)

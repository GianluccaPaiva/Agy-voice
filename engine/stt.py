import os
import threading
from typing import Optional, Callable
import numpy as np
from faster_whisper import WhisperModel

class FasterWhisperSTT:
    """Motor de transcrição Speech-to-Text baseado em Faster-Whisper quantizado em int8 na RAM."""

    def __init__(self, model_name: str = "base", on_progress: Optional[Callable[[str, bool, str], None]] = None):
        self.model_name = model_name
        self.on_progress = on_progress
        self._lock = threading.Lock()
        self.num_threads = max(1, (os.cpu_count() or 4) // 2)
        
        print(f" Carregando Faster-Whisper [{self.model_name}] (threads={self.num_threads})...")
        self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8", cpu_threads=self.num_threads)

    def trocar_modelo(self, novo_modelo: str) -> bool:
        """Carrega um novo modelo na RAM de forma segura."""
        try:
            if self.on_progress:
                self.on_progress(novo_modelo, True, f"⏳ Carregando modelo Whisper '{novo_modelo}' na RAM...")
            
            novo_obj = WhisperModel(novo_modelo, device="cpu", compute_type="int8", cpu_threads=self.num_threads)
            
            with self._lock:
                self._model = novo_obj
                self.model_name = novo_modelo

            if self.on_progress:
                self.on_progress(novo_modelo, False, f"✅ Modelo Whisper '{novo_modelo}' pronto para uso!")
            print(f"✅ Modelo Whisper alterado para '{novo_modelo}'!")
            return True
        except Exception as e:
            print(f"❌ Erro ao carregar modelo Whisper '{novo_modelo}': {e}")
            if self.on_progress:
                self.on_progress(novo_modelo, False, f"❌ Falha ao carregar modelo '{novo_modelo}': {e}")
            return False

    def transcrever(self, audio_array: np.ndarray, modo_rapido: bool = False) -> str:
        if audio_array is None or len(audio_array) == 0:
            return ""
        beam = 1 if modo_rapido else 3
        with self._lock:
            segmentos, _ = self._model.transcribe(
                audio_array,
                language="pt",
                beam_size=beam,
                best_of=1 if modo_rapido else 2,
                without_timestamps=True,
                initial_prompt="AGY, agy, adaj, adai, Antigravity, sair da conversa."
            )
            return " ".join([s.text for s in segmentos]).strip()

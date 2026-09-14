import threading
from typing import Callable, Type, Dict, List, Any
from core.events import BaseEvent

class EventBus:
    """
    Padrão Observer / Publicador-Assinante (Pub-Sub) thread-safe.
    Permite desacoplar completamente o motor de áudio das interfaces (GUI, CLI, Tray).
    """
    def __init__(self):
        self._listeners: Dict[Type[BaseEvent], List[Callable[[Any], None]]] = {}
        self._global_listeners: List[Callable[[BaseEvent], None]] = []
        self._lock = threading.RLock()

    def subscribe(self, event_type: Type[BaseEvent], callback: Callable[[Any], None]) -> None:
        """Inscreve um callback para um tipo específico de evento."""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[BaseEvent], None]) -> None:
        """Inscreve um callback para todos os eventos disparados."""
        with self._lock:
            if callback not in self._global_listeners:
                self._global_listeners.append(callback)

    def unsubscribe(self, event_type: Type[BaseEvent], callback: Callable[[Any], None]) -> None:
        with self._lock:
            if event_type in self._listeners and callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)

    def publish(self, event: BaseEvent) -> None:
        """Publica um evento para todos os ouvintes inscritos."""
        with self._lock:
            event_type = type(event)
            listeners = list(self._listeners.get(event_type, []))
            globals_ = list(self._global_listeners)

        for callback in listeners:
            try:
                callback(event)
            except Exception as e:
                print(f"⚠️ Erro no listener do evento {event_type.__name__}: {e}")

        for callback in globals_:
            try:
                callback(event)
            except Exception as e:
                print(f"⚠️ Erro no global listener: {e}")

# Instância padrão global para conveniência
global_event_bus = EventBus()

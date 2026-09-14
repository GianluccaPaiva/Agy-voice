from dataclasses import dataclass
from core.states import AppState

class BaseEvent:
    """Evento base do sistema."""
    pass

@dataclass
class StateChangedEvent(BaseEvent):
    new_state: AppState

@dataclass
class VolumeLevelEvent(BaseEvent):
    volume: float

@dataclass
class VADStatusEvent(BaseEvent):
    status_text: str

@dataclass
class ChatMessageEvent(BaseEvent):
    sender: str  # "user", "agy", "system"
    message: str

@dataclass
class ModelLoadProgressEvent(BaseEvent):
    model_name: str
    is_loading: bool
    message: str

@dataclass
class PermissionRequestEvent(BaseEvent):
    request_id: str
    action_type: str
    description: str
    details: str

@dataclass
class PermissionResponseEvent(BaseEvent):
    request_id: str
    approved: bool


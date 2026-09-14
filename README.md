# AGY Voice Frontend (CLI Interceptor)

Frontend de voz que intercepta a CLI do `agy` no terminal operando **100% em memória RAM** (Zero Disk I/O):
1. **Entrada (RAM)**: Grava o áudio diretamente em arrays NumPy na memória RAM e transcreve via `faster-whisper` sem salvar arquivos WAV no disco/SSD.
2. **Processamento**: Executa o `agy` em segundo plano (`agy --print "<prompt>" -c`) mantendo o contexto da sessão.
3. **Saída (RAM)**: Converte a resposta em voz via `edge-tts` usando buffers em memória (`io.BytesIO`) e reproduz no alto-falante.


---

## 📋 Pré-requisitos

1. **Python 3.10 ou superior** instalado no sistema.
2. **Antigravity CLI (`agy`)** instalado e autenticado no terminal:
   - Verifique digitando `agy --help` no terminal.
3. **Microfone e Fone de Ouvido/Alto-falante** conectados e configurados no Windows.

---

## 📦 Dependências do Projeto

As dependências estão listadas em [`requirements.txt`](file:///C:/Users/gianl/agy-voice-frontend/requirements.txt):

| Pacote | Função no Projeto |
| :--- | :--- |
| **`faster-whisper`** | Motor de transcrição de fala local (STT) ultrarrápido em CPU com quantização `int8`. |
| **`edge-tts`** | Síntese de voz neural natural da Microsoft (TTS) em português e outros idiomas. |
| **`pygame`** | Reprodução de áudio diretamente da memória RAM via `io.BytesIO`. |
| **`sounddevice`** | Captura contínua de áudio do microfone em buffers float32. |
| **`soundfile`** | Manipulação de áudio e formatos de dados brutos. |
| **`numpy`** | Processamento matricial de sinais e cálculo de RMS para o VAD em tempo real. |
| **`customtkinter`** | Framework moderno de interface gráfica dark-mode para Desktop. |
| **`pystray`** | Minimização e execução do aplicativo na bandeja do sistema (*System Tray*). |
| **`pillow` (PIL)** | Renderização matemática do Círculo Cromático HSV e ícones dinâmicos. |

---

## 🛠️ Instalação Passo a Passo

### 1. Clonar o Repositório
```bash
git clone https://github.com/SEU_USUARIO/agy-voice-frontend.git
cd agy-voice-frontend
```

### 2. Criar e Ativar o Ambiente Virtual (`.venv`)

* **No Windows (PowerShell)**:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
* **No Windows (CMD)**:
  ```cmd
  python -m venv .venv
  .\.venv\Scripts\activate.bat
  ```

### 3. Instalar as Dependências
```bash
pip install -r requirements.txt
```

---

## 🚀 Como Executar

### 🖥️ Opção 1: Hub Visual Nativo para Desktop (Recomendado)
Um aplicativo de desktop moderno com **Glowing Energy Orb**, feed de chat e controles:
* **🎙️ Seletor de Qualidade Whisper (STT)**: Escolha a precisão da transcrição em tempo real (`Tiny`, `Base`, `Small`, `Medium` ou `Turbo`) com troca a quente em memória RAM.
* **🎨 Círculo de Cores Interativo**: Personalize livremente as cores do Orb tanto para o modo **⚡ Acordado** quanto para o modo **💤 Standby** usando o círculo cromático HSV suave, paletas de clique rápido ou seletor avançado.
* **📁 Configurações Fixas em `setting/`**: Todas as preferências (qualidade whisper, voz, opacidade, cores, fixação no topo e último estado) são salvas automaticamente em [`setting/config.json`](file:///C:/Users/gianl/agy-voice-frontend/setting/config.json).
* **⚙ Botão de Configurações**: Ajuste a **Transparência / Opacidade** da janela em tempo real (de 35% a 100%) e ative **"Fixar Sempre no Topo"**.
* **🔕 Execução em 2º Plano (Ao fechar no 'X')**: Ao clicar no 'X' da janela, o app não fecha; ele é ocultado para a bandeja do sistema (*System Tray* / perto do relógio) e continua ouvindo e respondendo por voz.
* **🛑 Encerramento Definitivo**: Para fechar de verdade, use o botão vermelho dentro do menu **⚙ Configurações** ou clique com botão direito no ícone da bandeja $\rightarrow$ **Encerrar Definitivamente**.
* **💬 Modo Compacto / Widget**: Recolha o feed de chat e deixe apenas o Orb compacto na tela.
* **No PowerShell**: Execute [`.\run_hub.ps1`](file:///C:/Users/gianl/agy-voice-frontend/run_hub.ps1)
* **No Windows Explorer / CMD**: Duplo clique em [`run_hub.bat`](file:///C:/Users/gianl/agy-voice-frontend/run_hub.bat) ou `python gui_hub.py`

---

### 💻 Opção 2: Versão em Linha de Comando (Terminal)
* **No PowerShell**: Execute [`.\run.ps1`](file:///C:/Users/gianl/agy-voice-frontend/run.ps1)
* **No Windows Explorer / CMD**: Duplo clique em [`run.bat`](file:///C:/Users/gianl/agy-voice-frontend/run.bat) ou `python main.py`

---

## 🏛️ Arquitetura de Software & Design Patterns

O projeto foi estruturado seguindo princípios de **Clean Architecture** e **SOLID**:

```text
agy-voice-frontend/
├── config/             # Configurações tipadas (AppConfig) e persistência em setting/
│   ├── manager.py
│   └── settings.py
├── core/               # Núcleo da Máquina de Estados e EventBus (Observer Pattern)
│   ├── event_bus.py
│   ├── events.py
│   └── states.py
├── engine/             # Motores de IA e Pipeline de Áudio 100% em RAM
│   ├── agy_bridge.py   # Execução subprocesso agy CLI
│   ├── stt.py          # Faster-Whisper STT com hot-swap
│   ├── tts.py          # Edge-TTS e reprodução com Barge-in
│   ├── vad.py          # Gravador VAD e Pré-filtro acústico
│   ├── text_processor.py # Matcher fonético de Wake Word e intenções
│   └── voice_controller.py # Orquestrador central do Pipeline
├── ui/                 # Componentes Visuais Desacoplados (CustomTkinter)
│   ├── color_wheel.py  # Círculo Cromático HSV e cálculo de saturação
│   ├── orb.py          # Canvas com Glowing Energy Orb animado
│   ├── chat_feed.py    # Painel de transcrições em tempo real
│   ├── settings_view.py# Painel de configurações inline
│   ├── tray.py         # Gerenciador da Bandeja do Sistema (pystray)
│   └── main_window.py  # Janela Principal conectada via EventBus
├── setting/
│   └── config.json     # Preferências salvas
├── gui_hub.py          # Entrypoint GUI Desktop
└── main.py             # Entrypoint Terminal CLI
```

### Principais Padrões Utilizados & O que é esse Modelo Arquitetural:

Este projeto adota uma fusão de **Clean Architecture (Arquitetura Limpa)**, **Arquitetura Orientada a Eventos (EDA / Event-Driven)** e o padrão **Pipeline**:

1. **Clean Architecture (Separação por Camadas de Responsabilidade)**:
   - **Camada de Domínio (`core/`)**: Define as entidades fundamentais, estados (`AppState`) e eventos do sistema. Não depende de nenhuma biblioteca externa (nem do CustomTkinter, nem do Pygame, nem do Faster-Whisper).
   - **Camada de Aplicação / Motores (`engine/`)**: Contém a inteligência de processamento de áudio, transcrição e comunicação com a IA.
   - **Camada de Apresentação / Adaptadores (`ui/`, `main.py`)**: As interfaces gráficas e de linha de comando são meros "clientes" ou "adaptadores" que apenas exibem dados e capturam cliques do usuário.
   - **Regra de Dependência**: O fluxo de dependência aponta sempre para dentro. A lógica de voz não sabe e não se importa se a interface é um aplicativo Desktop nativo, um terminal CLI ou um futuro dashboard Web.

2. **Event-Driven Architecture (EDA) & Observer Pattern (`EventBus`)**:
   - Em vez de acoplar o gravador de áudio chamando funções da janela gráfica diretamente, o motor apenas emite eventos (`StateChangedEvent`, `ChatMessageEvent`, `VolumeLevelEvent`).
   - Múltiplos componentes podem "escutar" o mesmo evento simultaneamente (por exemplo: ao mudar de estado, o Orb muda de cor, o botão altera seu texto e o ícone da barra de tarefas atualiza sua imagem de forma independente e thread-safe).

3. **Pipeline Pattern (Processamento In-Memory)**:
   - O fluxo de dados opera como uma linha de montagem linear e estritamente em RAM:
     $$\text{Mic Audio (NumPy)} \rightarrow \text{VAD Filter} \rightarrow \text{Whisper STT} \rightarrow \text{AGY CLI Bridge} \rightarrow \text{Edge-TTS Buffer} \rightarrow \text{Speaker}$$
   - Elimina travas de I/O em disco, arquivos temporários no SSD e problemas de permissão no Windows.

4. **Data Transfer Object (DTO) & Repository (`config/`)**:
   - As configurações são manipuladas através de uma classe de dados com tipagem estática (`AppConfig`), garantindo autocompletar na IDE e validação automática de tipos.

---

### 💎 Princípios SOLID Aplicados na Prática:

| Princípio | Aplicação no Projeto |
| :--- | :--- |
| **S — Single Responsibility Principle** | Cada módulo tem um propósito único: `vad.py` apenas grava e calcula RMS, `stt.py` apenas faz inferência no Whisper, `tts.py` apenas sintetiza e toca áudio, e `manager.py` apenas persiste configurações em disco. |
| **O — Open/Closed Principle** | Novos recursos são adicionados estendendo o `EventBus` com novos eventos (`BaseEvent`) e novos ouvintes, sem necessidade de modificar o loop principal do `VoiceController`. |
| **L — Liskov Substitution Principle** | Todos os eventos derivam de `BaseEvent`, permitindo que o despachador do `EventBus` processe qualquer evento de forma uniforme e intercambiável. |
| **I — Interface Segregation Principle** | Componentes da interface (`GlowingOrbCanvas`, `ChatFeedComponent`) expõem e consomem apenas os métodos e eventos estritamente necessários para o seu funcionamento visual. |
| **D — Dependency Inversion Principle** | O motor central (`VoiceController`) não depende do CustomTkinter nem de janelas de SO; ele depende da abstração de eventos do `EventBus`. Tanto o app Desktop (`gui_hub.py`) quanto o Terminal (`main.py`) utilizam o mesmo motor idêntico sem acoplamento. |






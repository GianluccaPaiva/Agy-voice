import asyncio
import json
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable

@dataclass
class AgyExecutionResult:
    """Resultado estruturado retornado pela ponte do agy CLI."""
    response_text: str
    requer_permissao: bool = False
    action_type: str = ""          # ex: "command", "file_edit", "custom"
    action_description: str = ""   # ex: "Executar comando no terminal"
    action_details: str = ""       # ex: "Get-ChildItem -File ..."
    tool_name: str = ""
    tool_parameters: Dict[str, Any] = field(default_factory=dict)
    raw_error: str = ""
    sucesso: bool = True

class AgyBridge:
    """Ponte de comunicação assíncrona streaming com o CLI do agy (`agy.exe`) com interceptação de permissões."""

    @staticmethod
    async def executar_streaming(
        prompt: str,
        primeira_interacao: bool = False,
        skip_permissions: bool = False,
        on_text_delta: Optional[Callable[[str], None]] = None,
        on_sentence_ready: Optional[Callable[[str], None]] = None
    ) -> AgyExecutionResult:
        """
        Executa o comando `agy --print '<prompt>' --output-format stream-json`
        com leitura em tempo real (linha por linha) do stdout para TTFA (Time To First Audio) mínimo.
        """
        comando = ["agy", "--print", prompt, "--output-format", "stream-json"]
        if not primeira_interacao:
            comando.append("-c")
        if skip_permissions:
            comando.append("--dangerously-skip-permissions")

        try:
            processo = await asyncio.create_subprocess_exec(
                *comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            full_response_parts: List[str] = []
            buffer_frase: str = ""
            requer_permissao = False
            last_tool_name = ""
            last_tool_params: Dict[str, Any] = {}
            denied_actions: List[Dict[str, Any]] = []
            raw_stdout_lines: List[str] = []

            # Leitura do stdout linha a linha em tempo real
            while True:
                line_bytes = await processo.stdout.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                raw_stdout_lines.append(line)

                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        event_type = data.get("event")

                        if event_type == "step_update":
                            step_update = data.get("step_update", {})
                            step_type = step_update.get("step_type")

                            if step_type == "agent_response":
                                delta = step_update.get("text_delta", "")
                                if delta:
                                    full_response_parts.append(delta)
                                    if on_text_delta:
                                        on_text_delta(delta)

                                    buffer_frase += delta
                                    # Emite sentença pronta assim que pontuação ou quebra de linha for encontrada
                                    if re.search(r'[.!?:\n]\s*$', buffer_frase) and len(buffer_frase.strip()) > 3:
                                        if on_sentence_ready:
                                            on_sentence_ready(buffer_frase.strip())
                                        buffer_frase = ""

                            elif step_type == "tool":
                                last_tool_name = step_update.get("tool_name", "")
                                tool_info = step_update.get("tool_info", {})
                                if "parameters" in tool_info:
                                    last_tool_params = tool_info.get("parameters", {})

                                err = step_update.get("error", {})
                                err_msg = str(err.get("message", ""))
                                if "permission check failed" in err_msg or "user denied permission" in err_msg:
                                    requer_permissao = True

                        elif event_type == "result":
                            result = data.get("result", {})
                            resp_final = result.get("response", "").strip()
                            if resp_final and not full_response_parts:
                                full_response_parts.append(resp_final)
                            denied_actions = result.get("denied_actions", [])
                            if denied_actions:
                                requer_permissao = True

                    except Exception as parse_err:
                        print(f"⚠️ Erro ao parsear linha stream-json: {parse_err}")
                else:
                    if "a tool required the" in line and "permission" in line:
                        requer_permissao = True

            # Se restou alguma frase final no buffer
            if buffer_frase.strip() and on_sentence_ready:
                on_sentence_ready(buffer_frase.strip())

            _, stderr_bytes = await processo.communicate()
            stderr_str = stderr_bytes.decode("utf-8", errors="replace").strip()

            response_text = "".join(full_response_parts).strip()

            if denied_actions or requer_permissao or ("permission" in stderr_str and "denied" in stderr_str):
                requer_permissao = True

            action_type = "command"
            action_description = "Executar ação no sistema"
            action_details = ""

            if last_tool_name == "run_command":
                action_type = "command"
                action_description = "Executar comando no terminal"
                action_details = str(last_tool_params.get("CommandLine", "")).strip()
            elif last_tool_name in ["write_to_file", "replace_file_content", "multi_replace_file_content", "sed_file"]:
                action_type = "file_edit"
                action_description = "Criar ou editar arquivo no projeto"
                action_details = str(last_tool_params.get("TargetFile", last_tool_params.get("TargetDirectory", ""))).strip()
            elif last_tool_name:
                action_type = "tool"
                action_description = f"Executar ferramenta `{last_tool_name}`"
                action_details = json.dumps(last_tool_params, ensure_ascii=False) if last_tool_params else ""
            elif denied_actions:
                action_type = denied_actions[0].get("action", "command")
                action_description = f"Permissão para {denied_actions[0].get('display_name', action_type)}"

            if not requer_permissao:
                if not response_text and raw_stdout_lines:
                    response_text = "\n".join(raw_stdout_lines)
                return AgyExecutionResult(
                    response_text=response_text or "Concluído.",
                    requer_permissao=False,
                    sucesso=(processo.returncode == 0)
                )

            return AgyExecutionResult(
                response_text=response_text,
                requer_permissao=True,
                action_type=action_type,
                action_description=action_description,
                action_details=action_details,
                tool_name=last_tool_name,
                tool_parameters=last_tool_params,
                raw_error=stderr_str,
                sucesso=True
            )

        except Exception as e:
            print(f"❌ Falha ao invocar processo agy: {e}")
            return AgyExecutionResult(
                response_text=f"Desculpe, não consegui me comunicar com o agy: {e}",
                requer_permissao=False,
                sucesso=False,
                raw_error=str(e)
            )

    @classmethod
    async def executar(
        cls,
        prompt: str,
        primeira_interacao: bool = False,
        skip_permissions: bool = False
    ) -> AgyExecutionResult:
        """Compatibilidade direta com interface padrão."""
        return await cls.executar_streaming(
            prompt=prompt,
            primeira_interacao=primeira_interacao,
            skip_permissions=skip_permissions
        )

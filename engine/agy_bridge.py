import asyncio
import subprocess

class AgyBridge:
    """Ponte de comunicação assíncrona com o CLI do agy (`agy.exe`)."""

    @staticmethod
    async def executar(prompt: str, primeira_interacao: bool = False) -> str:
        """
        Executa o comando `agy --print '<prompt>'` e anexa `-c` para manter o contexto nas perguntas seguintes.
        """
        comando = ["agy", "--print", prompt]
        if not primeira_interacao:
            comando.append("-c")

        try:
            processo = await asyncio.create_subprocess_exec(
                *comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await processo.communicate()

            if processo.returncode != 0:
                erro = stderr.decode("utf-8", errors="replace").strip()
                print(f"❌ Erro retornado pelo agy CLI: {erro}")
                return "Desculpe, ocorreu um erro na execução do agy CLI."

            return stdout.decode("utf-8", errors="replace").strip()

        except Exception as e:
            print(f"❌ Falha ao invocar processo agy: {e}")
            return f"Desculpe, não consegui me comunicar com o agy: {e}"

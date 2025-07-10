from langchain.tools import tool
import subprocess
import os

class FileTools:

    @tool("Read a file from the local filesystem")
    def read_file(path: str) -> str:
        """
        Reads the content of a file. The path must be relative or absolute.
        Useful for viewing the current status of a code file or configuration file.
        Make sure that you add the path given bevor with directory to the filepath.
        example: '{repository path}/{path to the file inside the repository}'
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"Fehler: Datei nicht gefunden: {path}"
        except Exception as e:
            return f"Fehler beim Lesen der Datei: {str(e)}"

    @tool("Write content to a file on the local filesystem")
    def write_file(data: dict) -> str:
        """Writes content to a file.
        Expects a dictionary with:
        - 'path': path to the file. Make sure that you add the path given bevor with directory to the filepath.
        - 'content': content of the file, attention the file will be completely replaced

        example:
        {
            "path": "{repository path}/{path to the file inside the repository}",
            "content": "def foo(): return 42"
        }
        """
        path = data.get("path")
        content = data.get("content")
        if not path or content is None:
            return "Fehler: 'path' und 'content' müssen angegeben sein."

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Inhalt erfolgreich in {path} geschrieben."
        except Exception as e:
            return f"Fehler beim Schreiben in die Datei: {str(e)}"

    @tool("Execute git add command")
    def git_add(inputs: dict) -> str:
        """
        Executes `git add` for a specific file or an entire folder.
        Useful if an agent has changed a file and wants to prepare it for a commit.

        Input:
            {
                "repo_path": "Path to the Git repository (e.g. '/repos/repo_{number}')",
                "file_path": "Path to the file relative to repo_path (e.g. 'src/main.py')"
            }

        Output:
            Success message or error message in the event of problems.
        """
        try:
            repo_path = inputs.get("repo_path")
            file_path = inputs.get("file_path")

            if not repo_path or not file_path:
                return "Fehler: repo_path und file_path müssen angegeben werden."

            abs_repo_path = os.path.abspath(repo_path)
            full_file_path = os.path.join(abs_repo_path, file_path)

            if not os.path.exists(full_file_path):
                return f"Fehler: Datei existiert nicht: {full_file_path}"

            subprocess.run(
                ["git", "add", file_path],
                cwd=abs_repo_path,
                check=True
            )

            return f"Datei erfolgreich zur Git-Staging-Area hinzugefügt: {file_path}"

        except subprocess.CalledProcessError as e:
            return f"Fehler beim Ausführen von git add: {e}"
        except Exception as e:
            return f"Unerwarteter Fehler: {str(e)}"

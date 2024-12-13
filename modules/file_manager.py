import os
from rich.console import Console
from rich.prompt import Prompt

console = Console()

class FileManager:
    def __init__(self, model):
        self.model = model
        
    def create_file(self, path, content):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            console.print(f"[green]Created: {path}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error creating file: {e}[/red]")
            return False
            
    def read_file(self, path):
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            console.print(f"[red]Error reading file: {e}[/red]")
            return None
            
    def edit_file(self, path, content):
        try:
            with open(path, "w") as f:
                f.write(content)
            console.print(f"[green]Updated: {path}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error editing file: {e}[/red]")
            return False
            
    def delete_file(self, path):
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                os.rmdir(path)
            console.print(f"[green]Removed: {path}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error deleting file/directory: {e}[/red]")
            return False 
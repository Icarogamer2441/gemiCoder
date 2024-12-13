import os
from dotenv import load_dotenv
import google.generativeai as genai
from rich.console import Console
from rich.prompt import Prompt
from modules.project_manager import ProjectManager
from modules.chat_manager import ChatManager
from modules.file_manager import FileManager
import json

# Load environment variables
load_dotenv()

# Configure Gemini AI
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash-exp')

console = Console()

class GemiCoder:
    def __init__(self):
        self.project_manager = ProjectManager()
        self.chat_manager = ChatManager()
        self.file_manager = FileManager(model)
        self.persistent_files = {}  # Armazenar arquivos por projeto
        
    def get_project_structure(self, project_dir):
        """Retorna uma lista com todos os caminhos de arquivos no projeto"""
        file_paths = []
        for root, dirs, files in os.walk(project_dir):
            # Ignorar diretórios ocultos e __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if not file.startswith('.'):
                    # Converter para caminho relativo ao diretório do projeto
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, project_dir)
                    file_paths.append(rel_path)
        
        return sorted(file_paths)

    def start_project_chat(self, project, project_dir, model):
        # Criar diretório de chats se não existir
        chats_dir = "chats"
        if not os.path.exists(chats_dir):
            os.makedirs(chats_dir)
        
        # Nome do arquivo de chat baseado no projeto
        chat_file = os.path.join(chats_dir, f"chat_{project}.json")
        
        # Carregar ou iniciar histórico
        try:
            if os.path.exists(chat_file):
                try:
                    with open(chat_file, "r", encoding='utf-8') as f:
                        saved_history = json.load(f)
                except json.JSONDecodeError:
                    console.print("[yellow]Warning: Chat history file is corrupted. Starting new chat.[/yellow]")
                    saved_history = []
            else:
                saved_history = []
        except Exception as e:
            console.print(f"[yellow]Error loading chat history: {str(e)}. Starting new chat.[/yellow]")
            saved_history = []
        
        # Garantir que temos um histórico inicial
        if not saved_history:
            # Mensagem inicial para contextualizar a IA
            system_prompt = f"""You are managing the project '{project}' in directory '{project_dir}'.
            You can create, edit, read, move and delete files, and run terminal commands.
            Always respond with a JSON array of actions when asked to modify the project.
            Example action format:
            [
                {{
                    "action_type": "create",
                    "path": "src/main.py",
                    "content": "print('Hello World')",
                    "description": "Create main.py file with hello world code"
                }}
            ]"""
            saved_history = [{
                "parts": [{"text": system_prompt}],
                "role": "user"
            }]
        
        # Converter histórico salvo para o formato do Gemini
        chat_history = []
        for msg in saved_history:
            try:
                if isinstance(msg, dict):
                    if 'content' in msg:
                        # Converter formato antigo para novo
                        chat_history.append({
                            "parts": [{"text": msg['content']}],
                            "role": msg['role']
                        })
                    elif 'parts' in msg and 'role' in msg:
                        # Já está no formato correto
                        chat_history.append(msg)
            except Exception as e:
                console.print(f"[yellow]Error processing chat message: {str(e)}[/yellow]")
        
        chat = model.start_chat(history=chat_history)
        return chat, chat_file

    def process_custom_command(self, command, project_dir, chat, project):
        """Processa comandos customizados começando com /"""
        if command.startswith('/help'):
            console.print("\n[bold]Available commands:[/bold]")
            console.print("""
/help           - Show this help message
/codebase       - Show all project files and analyze them
/codebase query - Analyze project files with specific query
/add-file path  - Add file to active context
/add-folder [path] - Add all files from folder (current dir if no path)
/remove-file path - Remove file from active context
/exit           - Exit current project

[bold]Examples:[/bold]
/codebase find security issues
/add-file src/main.py
/add-folder src/utils
/remove-file config.json
""")
            return True
        
        elif command.startswith('/add-folder'):
            folder_path = command[11:].strip()
            if folder_path:
                full_folder_path = os.path.join(project_dir, folder_path)
            else:
                full_folder_path = project_dir
            
            if not os.path.exists(full_folder_path):
                console.print(f"[red]Folder not found: {folder_path}[/red]")
                return True
            
            # Extensões de arquivo que são consideradas texto
            text_extensions = {
                '.txt', '.py', '.js', '.html', '.css', '.json', '.md', '.yml', 
                '.yaml', '.xml', '.csv', '.ini', '.conf', '.sh', '.bat', '.ps1',
                '.env', '.gitignore', '.sql', '.java', '.cpp', '.c', '.h', '.hpp',
                '.ts', '.jsx', '.tsx', '.vue', '.php', '.rb', '.pl', '.go'
            }
            
            # Inicializar dicionário do projeto se necessário
            if project not in self.persistent_files:
                self.persistent_files[project] = {}
            
            files_added = 0
            
            # Listar apenas arquivos no diretório especificado (sem subdiretórios)
            for file in os.listdir(full_folder_path):
                file_path = os.path.join(full_folder_path, file)
                if os.path.isfile(file_path):
                    # Verificar se é arquivo de texto
                    if os.path.splitext(file)[1].lower() in text_extensions:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # Usar caminho relativo ao projeto
                                rel_path = os.path.relpath(file_path, project_dir)
                                self.persistent_files[project][rel_path] = content
                                files_added += 1
                        except Exception as e:
                            console.print(f"[yellow]Could not read {file}: {str(e)}[/yellow]")
            
            if files_added > 0:
                console.print(f"[green]Added {files_added} files from {folder_path or '.'} to persistent files[/green]")
            else:
                console.print("[yellow]No text files found in the specified folder[/yellow]")
            return True
        
        elif command.startswith('/add-file'):
            file_path = command[10:].strip()
            if not file_path:
                console.print("[red]Please specify a file path[/red]")
                return True
            
            full_path = os.path.join(project_dir, file_path)
            try:
                content = self.file_manager.read_file(full_path)
                if content:
                    if project not in self.persistent_files:
                        self.persistent_files[project] = {}
                    self.persistent_files[project][file_path] = content
                    console.print(f"[green]Added {file_path} to persistent files[/green]")
            except Exception as e:
                console.print(f"[red]Error reading file: {str(e)}[/red]")
            return True
        
        elif command.startswith('/remove-file'):
            file_path = command[12:].strip()
            if not file_path:
                console.print("[red]Please specify a file path[/red]")
                return True
            
            if project in self.persistent_files and file_path in self.persistent_files[project]:
                del self.persistent_files[project][file_path]
                console.print(f"[green]Removed {file_path} from persistent files[/green]")
            else:
                console.print(f"[yellow]File {file_path} not in persistent list[/yellow]")
            return True
        
        elif command.startswith('/codebase'):
            prompt = command[9:].strip()
            files = self.get_project_structure(project_dir)
            
            # Lista para armazenar conteúdo dos arquivos
            file_contents = []
            
            # Extensões de arquivo que são consideradas texto
            text_extensions = {
                '.txt', '.py', '.js', '.html', '.css', '.json', '.md', '.yml', 
                '.yaml', '.xml', '.csv', '.ini', '.conf', '.sh', '.bat', '.ps1',
                '.env', '.gitignore', '.sql', '.java', '.cpp', '.c', '.h', '.hpp',
                '.ts', '.jsx', '.tsx', '.vue', '.php', '.rb', '.pl', '.go'
            }
            
            for file in files:
                full_path = os.path.join(project_dir, file)
                # Verificar se é arquivo de texto baseado na extensão
                if os.path.splitext(file)[1].lower() in text_extensions:
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            file_contents.append(f"""
File: {file}
```
{content}
```
""")
                    except Exception as e:
                        console.print(f"[yellow]Could not read {file}: {str(e)}[/yellow]")
            
            if not prompt:
                # Se não houver prompt, mostrar estrutura e enviar para IA
                console.print("\n[bold]Project structure:[/bold]")
                for file in files:
                    console.print(f"- {file}")
                
                analysis_prompt = f"""Project structure and contents:

Files:
{chr(10).join(f'- {f}' for f in files)}

Contents:
{chr(10).join(file_contents)}

Please analyze the project structure and provide an overview of the codebase.
"""
            else:
                # Se houver prompt, usar na análise
                analysis_prompt = f"""Project structure and contents:

Files:
{chr(10).join(f'- {f}' for f in files)}

Contents:
{chr(10).join(file_contents)}

User query: {prompt}

Analyze the project based on the query, considering both structure and file contents.
"""
            
            try:
                response = chat.send_message(analysis_prompt)
                console.print("\n[bold]Analysis:[/bold]")
                console.print(response.text)
            except Exception as e:
                console.print(f"[red]Error analyzing codebase: {str(e)}[/red]")
            
            return True
        
        return False

    def show_persistent_files(self, project):
        """Mostra arquivos persistentes do projeto atual"""
        if project in self.persistent_files and self.persistent_files[project]:
            console.print("\n[bold]Active files:[/bold]")
            for file_path in self.persistent_files[project]:
                console.print(f"- {file_path}")
            console.print("")

    def main_menu(self):
        console.print("[bold blue]Welcome to GemiCoder![/bold blue]")
        
        while True:
            # Opção inicial
            projects_dir = "projects"
            if not os.path.exists(projects_dir):
                os.makedirs(projects_dir)
            
            projects = [d for d in os.listdir(projects_dir) 
                       if os.path.isdir(os.path.join(projects_dir, d))]
            
            if not projects:
                console.print("[yellow]No projects found[/yellow]")
                if Prompt.ask("Create new project?", choices=["y", "n"]) != "y":
                    return
                action = "create"
            else:
                action = Prompt.ask(
                    "What would you like to do?",
                    choices=["open", "create", "exit"]
                )
                
            if action == "exit":
                break
            
            if action == "create":
                project_name = Prompt.ask("Enter project name")
                if project_name in projects:
                    console.print("[red]Project already exists![/red]")
                    continue
                os.makedirs(os.path.join(projects_dir, project_name))
                project = project_name
            else:  # open
                project = Prompt.ask("Select project", choices=projects)
                
            project_dir = os.path.join(projects_dir, project)
            
            console.print(f"\n[bold green]Working on project: {project}[/bold green]")
            console.print("Type your request in natural language or 'exit' to quit")
            
            # Iniciar chat do projeto
            chat, chat_file = self.start_project_chat(project, project_dir, model)
            
            while True:
                # Mostrar arquivos persistentes antes de cada prompt
                self.show_persistent_files(project)
                
                prompt = Prompt.ask("\nWhat would you like me to do?")
                
                if prompt.lower() == 'exit':
                    break
                
                if prompt.startswith('/'):
                    if self.process_custom_command(prompt, project_dir, chat, project):
                        continue
                
                try:
                    # Adicionar conteúdo dos arquivos persistentes ao prompt
                    files_content = ""
                    if project in self.persistent_files:
                        for file_path, content in self.persistent_files[project].items():
                            files_content += f"\nFile: {file_path}\n```\n{content}\n```\n"
                    
                    if files_content:
                        full_prompt = f"""Active files in context:
{files_content}

User request: {prompt}"""
                    else:
                        full_prompt = prompt
                    
                    # Enviar prompt para o chat
                    response = chat.send_message(full_prompt)
                    text = response.text.strip()
                    
                    # Procurar por JSON na resposta
                    start = text.find('[')
                    end = text.rfind(']') + 1
                    
                    if start == -1 or end == 0:
                        console.print("\n[bold]AI Response:[/bold]")
                        console.print(text)
                        continue
                    
                    actions = json.loads(text[start:end])
                    
                    # Corrigir: Não duplicar o caminho do projeto
                    for action in actions:
                        if 'path' in action:
                            # Verificar se o caminho já inclui o diretório do projeto
                            if not action['path'].startswith(project_dir):
                                action['path'] = os.path.join(project_dir, action['path'])
                        if action['action_type'] == 'move':
                            if not action['content'].startswith(project_dir):
                                action['content'] = os.path.join(project_dir, action['content'])
                    
                    # Mostrar e confirmar ações
                    console.print("\n[bold]Proposed actions:[/bold]")
                    for action in actions:
                        console.print(f"\n- {action['description']}")
                        if action['action_type'] == 'terminal':
                            console.print(f"  Command: {action['content']}")
                    
                    if Prompt.ask("\nProceed with these actions?", choices=["y", "n"]) == "y":
                        for action in actions:
                            self.execute_action(action, chat)
                            # Se for uma ação de leitura, esperar por instruções adicionais
                            if action['action_type'] == 'read':
                                next_step = Prompt.ask("\nWhat would you like to do next?")
                                if next_step.lower() != 'exit':
                                    response = chat.send_message(next_step)
                                    text = response.text.strip()
                                    
                                    # Procurar por novas ações no formato JSON
                                    start = text.find('[')
                                    end = text.rfind(']') + 1
                                    
                                    if start != -1 and end != 0:
                                        new_actions = json.loads(text[start:end])
                                        console.print("\n[bold]Additional actions proposed:[/bold]")
                                        for new_action in new_actions:
                                            console.print(f"\n- {new_action['description']}")
                                            if new_action['action_type'] == 'terminal':
                                                console.print(f"  Command: {new_action['content']}")
                                        
                                        if Prompt.ask("\nProceed with these actions?", choices=["y", "n"]) == "y":
                                            for new_action in new_actions:
                                                self.execute_action(new_action, chat)
                                    else:
                                        console.print("\n[bold]AI Response:[/bold]")
                                        console.print(text)
                    
                    # Salvar histórico do chat
                    self.save_chat_history(chat, chat_file)
                
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
    
    def execute_action(self, action, chat):
        try:
            if action['action_type'] == 'create':
                if Prompt.ask(f"Create {action['path']}?", choices=["y", "n"]) == "y":
                    self.file_manager.create_file(action['path'], action['content'])
                    
            elif action['action_type'] == 'edit':
                if Prompt.ask(f"Edit {action['path']}?", choices=["y", "n"]) == "y":
                    self.file_manager.edit_file(action['path'], action['content'])
                    
            elif action['action_type'] == 'move':
                if Prompt.ask(f"Move {action['path']} to {action['content']}?", choices=["y", "n"]) == "y":
                    os.rename(action['path'], action['content'])
                    
            elif action['action_type'] == 'remove':
                if Prompt.ask(f"Remove {action['path']}?", choices=["y", "n"]) == "y":
                    self.file_manager.delete_file(action['path'])
                    
            elif action['action_type'] == 'terminal':
                if Prompt.ask(f"Run command: {action['content']}?", choices=["y", "n"]) == "y":
                    os.system(action['content'])
                    
        except Exception as e:
            console.print(f"[red]Error executing action: {str(e)}[/red]")

    def save_chat_history(self, chat, chat_file):
        # Converter histórico para formato serializável
        history_to_save = []
        for msg in chat.history:
            if hasattr(msg, 'parts') and hasattr(msg, 'role'):
                history_to_save.append({
                    "parts": [{"text": part.text} for part in msg.parts],
                    "role": msg.role
                })
        
        with open(chat_file, "w") as f:
            json.dump(history_to_save, f, indent=4)

if __name__ == "__main__":
    app = GemiCoder()
    app.main_menu() 
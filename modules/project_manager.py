import os
import json
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()

class ProjectManager:
    def __init__(self):
        self.projects_dir = "projects"
        self.ensure_projects_directory()
        
    def ensure_projects_directory(self):
        if not os.path.exists(self.projects_dir):
            os.makedirs(self.projects_dir)
            
    def create_new_project(self, model):
        name = Prompt.ask("Enter project name")
        description = Prompt.ask("Enter project description")
        
        project_dir = os.path.join(self.projects_dir, name)
        
        if os.path.exists(project_dir):
            console.print("[red]Project already exists![/red]")
            return
            
        os.makedirs(project_dir)
        
        project_info = {
            "name": name,
            "description": description,
            "steps": [],
            "status": "planning"
        }
        
        with open(os.path.join(project_dir, "project.json"), "w") as f:
            json.dump(project_info, f, indent=4)
            
        console.print(f"[green]Project {name} created successfully![/green]")
        self.plan_project_steps(model, project_dir)
        
    def plan_project_steps(self, model, project_dir):
        with open(os.path.join(project_dir, "project.json"), "r") as f:
            project_info = json.load(f)
            
        prompt = f"""
        Create a step-by-step plan for the following project:
        Name: {project_info['name']}
        Description: {project_info['description']}
        
        Return only a valid JSON array of objects, where each object has:
        - step_number (integer)
        - description (string)
        - files_to_create (array of strings)
        
        Example format:
        [
            {{
                "step_number": 1,
                "description": "Setup project structure",
                "files_to_create": ["src/main.py", "src/utils.py"]
            }},
            {{
                "step_number": 2,
                "description": "Implement core features",
                "files_to_create": ["src/features.py"]
            }}
        ]
        """
        
        try:
            response = model.generate_content(prompt)
            # Tenta encontrar o JSON na resposta usando um parser mais robusto
            text = response.text.strip()
            # Procura pelo primeiro '[' e último ']' para extrair apenas o JSON
            start = text.find('[')
            end = text.rfind(']') + 1
            
            if start == -1 or end == 0:
                raise ValueError("No JSON array found in response")
            
            json_str = text[start:end]
            steps = json.loads(json_str)
            
            if not isinstance(steps, list):
                raise ValueError("Response is not a list")
            
            for step in steps:
                console.print(f"\n[bold]Step {step['step_number']}:[/bold]")
                console.print(step['description'])
                console.print("\nFiles to create:")
                for file in step['files_to_create']:
                    console.print(f"- {file}")
                
                if Prompt.ask("Accept this step?", choices=["y", "n"]) == "y":
                    project_info['steps'].append(step)
                    if Prompt.ask("Create files for this step now?", choices=["y", "n"]) == "y":
                        self.create_project_files(model, project_dir, step)
            
            with open(os.path.join(project_dir, "project.json"), "w") as f:
                json.dump(project_info, f, indent=4)
            
        except Exception as e:
            console.print(f"[red]Error planning project steps: {str(e)}[/red]")
            console.print("[yellow]Creating default step structure...[/yellow]")
            
            # Criar estrutura padrão de passos
            default_steps = [
                {
                    "step_number": 1,
                    "description": "Project setup and basic structure",
                    "files_to_create": ["src/main.py", "README.md", "requirements.txt"]
                },
                {
                    "step_number": 2,
                    "description": "Implement core functionality",
                    "files_to_create": ["src/core.py"]
                },
                {
                    "step_number": 3,
                    "description": "Add tests and documentation",
                    "files_to_create": ["tests/test_core.py", "docs/README.md"]
                }
            ]
            
            for step in default_steps:
                console.print(f"\n[bold]Step {step['step_number']}:[/bold]")
                console.print(step['description'])
                console.print("\nFiles to create:")
                for file in step['files_to_create']:
                    console.print(f"- {file}")
                
                if Prompt.ask("Accept this step?", choices=["y", "n"]) == "y":
                    project_info['steps'].append(step)
                    if Prompt.ask("Create files for this step now?", choices=["y", "n"]) == "y":
                        self.create_project_files(model, project_dir, step)
                
            with open(os.path.join(project_dir, "project.json"), "w") as f:
                json.dump(project_info, f, indent=4)
            
    def list_projects(self):
        table = Table(title="Projects")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Status")
        
        for project in os.listdir(self.projects_dir):
            project_file = os.path.join(self.projects_dir, project, "project.json")
            if os.path.exists(project_file):
                with open(project_file, "r") as f:
                    info = json.load(f)
                    table.add_row(info["name"], info["description"], info["status"])
                    
        console.print(table)
        
    def open_project(self, model):
        projects = [d for d in os.listdir(self.projects_dir) 
                   if os.path.isdir(os.path.join(self.projects_dir, d))]
        
        if not projects:
            console.print("[red]No projects found![/red]")
            return
            
        project = Prompt.ask("Enter project name", choices=projects)
        project_dir = os.path.join(self.projects_dir, project)
        
        with open(os.path.join(project_dir, "project.json"), "r") as f:
            project_info = json.load(f)
            
        console.print(f"\n[bold]Project: {project_info['name']}[/bold]")
        console.print(f"Description: {project_info['description']}")
        console.print(f"Status: {project_info['status']}")
        
        for step in project_info['steps']:
            console.print(f"\nStep {step['step_number']}:")
            console.print(step['description'])
        
        if Prompt.ask("\nWould you like to check for pending files?", choices=["y", "n"]) == "y":
            self.create_pending_files(model, project_dir)
        
    def create_project_files(self, model, project_dir, step):
        console.print("\n[bold blue]Creating files for this step...[/bold blue]")
        
        for file_path in step['files_to_create']:
            full_path = os.path.join(project_dir, file_path)
            
            # Criar o prompt para o Gemini gerar o conteúdo do arquivo
            prompt = f"""
            Create the content for the file: {file_path}
            This file is part of step {step['step_number']}: {step['description']}
            
            Project context:
            - Project name: {os.path.basename(project_dir)}
            - File purpose: Generate appropriate content based on the file type and path
            - Use best practices and include comments
            
            Return only the file content, no explanations needed.
            """
            
            try:
                response = model.generate_content(prompt)
                content = response.text.strip()
                
                # Criar diretórios necessários
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Mostrar o conteúdo gerado para aprovação
                console.print(f"\n[bold]Generated content for {file_path}:[/bold]")
                console.print(content)
                
                if Prompt.ask("\nAccept this content?", choices=["y", "n"]) == "y":
                    with open(full_path, "w") as f:
                        f.write(content)
                    console.print(f"[green]File created: {file_path}[/green]")
                else:
                    console.print(f"[yellow]Skipped: {file_path}[/yellow]")
                    
            except Exception as e:
                console.print(f"[red]Error creating {file_path}: {str(e)}[/red]") 
        
    def create_pending_files(self, model, project_dir):
        with open(os.path.join(project_dir, "project.json"), "r") as f:
            project_info = json.load(f)
        
        console.print("\n[bold]Pending files from accepted steps:[/bold]")
        
        for step in project_info['steps']:
            console.print(f"\n[bold]Step {step['step_number']}:[/bold] {step['description']}")
            
            for file_path in step['files_to_create']:
                full_path = os.path.join(project_dir, file_path)
                
                if not os.path.exists(full_path):
                    console.print(f"- {file_path} [yellow](pending)[/yellow]")
                else:
                    console.print(f"- {file_path} [green](created)[/green]")
            
            if Prompt.ask("\nCreate pending files for this step?", choices=["y", "n"]) == "y":
                self.create_project_files(model, project_dir, step) 
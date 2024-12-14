import os
from dotenv import load_dotenv
import google.generativeai as genai
from rich.console import Console
from rich.prompt import Prompt
from modules.project_manager import ProjectManager
from modules.chat_manager import ChatManager
from modules.file_manager import FileManager
import json
import requests
from PIL import Image
from io import BytesIO

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
        self.persistent_files = {}
        self.base_dir = os.path.dirname(os.path.abspath(__file__))  # GemiCoder base directory
        
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

    def start_project_chat(self, project, project_dir, model, system_prompt):
        # Criar diretório de chats se não existir
        chats_dir = os.path.join(self.base_dir, "chats")
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
                        chat_history.append({
                            "parts": [{"text": msg['content']}],
                            "role": msg['role']
                        })
                    elif 'parts' in msg and 'role' in msg:
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
/is-web         - Enable enhanced web development mode
/add-image path - Add and analyze local image (supports relative/absolute paths)
/exit           - Exit current project

[bold]Examples:[/bold]
/codebase find security issues
/add-file src/main.py
/add-folder src/utils
/remove-file config.json
/is-web         # Enable beautiful web UI generation
/add-image ../designs/mockup.png
/add-image C:/Users/MyUser/Desktop/reference.jpg
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
        
        elif command.startswith('/is-web'):
            web_prompt = """From now on, when creating web projects or features, you should:

1. Be proactive and creative with features:
   - When user requests are not specific, expand them with modern features
   - Add complementary functionality that enhances user experience
   - Think about the full user journey and add necessary supporting features
   - Include admin/management interfaces when appropriate
   - Add analytics and monitoring capabilities
   - Implement smart defaults and best practices

2. Create comprehensive solutions:
   - Full authentication system with roles and permissions
   - User profiles and settings
   - Dashboard with relevant metrics
   - Search and filter capabilities
   - Export/import functionality
   - Notification systems
   - Error tracking and logging
   - API documentation when relevant

3. Implement modern UI libraries and assets:
   - Use Tailwind CSS for utility-first styling
   - Implement Material UI or Chakra UI components
   - Include icon libraries (Phosphor, Lucide, or Material Icons)
   - Use Framer Motion for smooth animations
   - Implement ShadcnUI for beautiful components
   - Use modern fonts (Inter, Roboto, etc.)
   - Include hero patterns or SVG backgrounds
   - Use gradients and glass morphism effects
   - Implement skeleton loaders from libraries
   - Use chart libraries (Chart.js, D3.js)
   - Include image optimization (next/image)

4. Create beautiful and creative layouts:
   - Use modern grid systems with auto-fit/auto-fill
   - Implement masonry layouts when appropriate
   - Create card-based designs with hover effects
   - Use sticky headers and navigation
   - Implement parallax scrolling effects
   - Add floating action buttons (FAB)
   - Create multi-level navigation menus
   - Use breadcrumbs for deep navigation
   - Implement sidebar navigation with collapsible sections
   - Add quick action toolbars
   - Create tabbed interfaces
   - Use accordions for content organization
   - Implement floating labels in forms
   - Add progress indicators
   - Create step wizards for complex forms

5. Focus on modern UI/UX patterns:
   - Clean and professional layouts
   - Smooth animations and transitions
   - Micro-interactions and feedback
   - Loading states and skeletons
   - Toast notifications with icons
   - Modal dialogs with animations
   - Drag and drop interfaces
   - Infinite scroll with loading indicators
   - Modern color schemes and typography
   - Dark/light theme with system preference
   - Custom scrollbars
   - Hover tooltips and popovers
   - Context menus
   - File upload with preview
   - Image cropping/editing

6. Implement complete responsiveness:
   - Mobile-first approach
   - Fluid layouts and grids
   - Touch-friendly interactions
   - Responsive images and media
   - Adaptive navigation (hamburger menus)
   - Breakpoints for all devices
   - Print styles when relevant
   - Responsive typography
   - Collapsible sections on mobile
   - Bottom navigation for mobile
   - Swipe gestures

7. Add advanced features automatically:
   - Real-time updates with WebSocket
   - Offline support with Service Workers
   - Form validation with error messages
   - Auto-save functionality
   - Rate limiting and throttling
   - Caching strategies
   - Image optimization and lazy loading
   - SEO optimization
   - Social sharing with preview cards
   - Keyboard shortcuts
   - Voice commands when appropriate
   - Screen reader support
   - Multi-language support
   - Cookie consent
   - GDPR compliance

8. Include security and performance:
   - CSRF protection
   - XSS prevention
   - Input sanitization
   - Rate limiting
   - Password policies
   - Session management
   - Performance monitoring
   - Load time optimization
   - Asset compression
   - Image optimization
   - Code splitting
   - Bundle optimization

9. Consider full infrastructure:
   - Database design with indexes
   - API architecture and endpoints
   - Caching layers
   - CDN configuration
   - Deployment scripts
   - CI/CD pipelines
   - Backup strategies
   - Monitoring setup
   - Error tracking
   - Analytics integration

10. Add developer experience features:
    - Comprehensive documentation
    - API testing suite
    - Development environment setup
    - Debug logging
    - Error tracking
    - Performance monitoring
    - Code formatting and linting
    - Git hooks and workflows
    - Component storybook
    - E2E testing
    - Unit testing
    - Integration testing

When user requests are not detailed, proactively add these features and create beautiful interfaces using modern UI libraries and components.
Always aim to create production-ready, scalable solutions with modern best practices and stunning visuals.

For example, if user asks for "Create a blog":
- Use Tailwind CSS with custom theme
- Implement Material UI components
- Add Phosphor icons throughout
- Create animated page transitions
- Add floating action buttons
- Implement masonry grid for posts
- Create beautiful cards with hover effects
- Add skeleton loaders
- Include dark/light mode toggle
- Create responsive navigation
- Add search with autocomplete
- Implement tag cloud with animations
- Create beautiful author profiles
- Add reading progress indicator
- Implement social sharing buttons
- Create newsletter subscription form
- Add related posts carousel
- Implement comment system with reactions
- Create category navigation
- Add beautiful 404 page
etc.

Respond with a confirmation if you understand these requirements."""

            try:
                response = chat.send_message(web_prompt)
                console.print("\n[bold green]Enhanced web development mode enabled![/bold green]")
                console.print("The AI will now create comprehensive web solutions with beautiful UI and advanced features automatically.")
                return True
            except Exception as e:
                console.print(f"[red]Error enabling web mode: {str(e)}[/red]")
                return True
        
        elif command.startswith('/add-image'):
            image_path = command[10:].strip()
            if not image_path:
                console.print("[red]Please provide the image path[/red]")
                return True
                
            try:
                # Handle relative paths from current directory
                if not os.path.isabs(image_path):
                    # Try relative to current directory first
                    full_path = os.path.abspath(image_path)
                    if not os.path.exists(full_path):
                        # If not found, try relative to project directory
                        full_path = os.path.join(project_dir, image_path)
                else:
                    full_path = image_path
                
                if not os.path.exists(full_path):
                    console.print(f"[red]Image not found: {image_path}[/red]")
                    return True
                
                console.print("[bold blue]Reading and analyzing local image...[/bold blue]")
                
                # Try to open and encode the image
                try:
                    with open(full_path, 'rb') as img_file:
                        image_bytes = img_file.read()
                        import base64
                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        
                        # Create the content parts with proper structure
                        content = [
                            {
                                "role": "user",
                                "parts": [
                                    {
                                        "inline_data": {
                                            "mime_type": "image/png",
                                            "data": image_base64
                                        }
                                    },
                                    {
                                        "text": """Please analyze this image and describe its visual aspects in detail:
                                        1. Overall layout and composition
                                        2. Color scheme and visual style
                                        3. UI elements and their arrangement (if applicable)
                                        4. Typography and text styling
                                        5. Visual patterns and design elements
                                        6. Spacing and proportions
                                        7. Any notable animations or interactive elements suggested by the design
                                        
                                        Focus on the visual design aspects that could be referenced in development.
                                        Be detailed but organized in your analysis."""
                                    }
                                ]
                            }
                        ]
                except Exception as e:
                    console.print(f"[red]Error reading image: {str(e)}[/red]")
                    return True
                
                # Get image analysis with retry
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        analysis = model.generate_content(content)
                        image_description = analysis.text
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            console.print(f"[yellow]Retry {attempt + 1}/{max_retries}: Analysis failed, retrying...[/yellow]")
                            continue
                        console.print(f"[red]Error analyzing image after {max_retries} attempts: {str(e)}[/red]")
                        return True
                
                console.print("\n[bold]Visual Analysis:[/bold]")
                console.print(image_description)
                
                # Ask user for implementation details
                console.print("\n[bold blue]What would you like to implement based on this design? (Type your request or 'skip' to continue)[/bold blue]")
                console.print("[dim]Example: Create a landing page with similar layout and colors[/dim]")
                user_prompt = Prompt.ask("Your implementation request")
                
                if user_prompt.lower() != 'skip':
                    # Send both image description and user prompt to chat
                    full_prompt = f"""Visual Reference:
{image_description}

Implementation Request: {user_prompt}

Based on the visual reference above and the implementation request, please:
1. Create a detailed plan for implementation
2. Follow the visual style from the reference
3. Include all necessary files and code
4. Add appropriate animations and interactions
5. Ensure responsive design

Respond with actions to create the implementation."""
                    
                    try:
                        response = chat.send_message(full_prompt)
                        console.print("\n[bold]Implementation Plan:[/bold]")
                        console.print(response.text)
                    except Exception as e:
                        console.print(f"[red]Error processing request: {str(e)}[/red]")
                
            except Exception as e:
                console.print(f"[red]Unexpected error: {str(e)}[/red]")
            
            return True
        
        elif command.startswith('/add-local-image'):
            image_path = command[15:].strip()
            if not image_path:
                console.print("[red]Please provide the image path[/red]")
                return True
                
            try:
                # Convert relative path to absolute if needed
                if not os.path.isabs(image_path):
                    image_path = os.path.join(os.getcwd(), image_path)
                
                console.print("[bold blue]Reading and analyzing local image...[/bold blue]")
                
                # Try to open the image
                try:
                    with open(image_path, 'rb') as img_file:
                        image_data = {
                            "mime_type": "image/jpeg",  # Adjust based on file type if needed
                            "data": img_file.read()
                        }
                except FileNotFoundError:
                    console.print(f"[red]Image file not found: {image_path}[/red]")
                    return True
                except Exception as e:
                    console.print(f"[red]Error reading image: {str(e)}[/red]")
                    return True
                
                # Create prompt for image analysis
                prompt = """Please analyze this image and describe its visual aspects in detail:
                1. Overall layout and composition
                2. Color scheme and visual style
                3. UI elements and their arrangement (if applicable)
                4. Typography and text styling
                5. Visual patterns and design elements
                6. Spacing and proportions
                7. Any notable animations or interactive elements suggested by the design
                
                Focus on the visual design aspects that could be referenced in development.
                Be detailed but organized in your analysis."""
                
                # Get image analysis with retry
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        analysis = model.generate_content([prompt, image_data])
                        image_description = analysis.text
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            console.print(f"[yellow]Retry {attempt + 1}/{max_retries}: Analysis failed, retrying...[/yellow]")
                            continue
                        console.print(f"[red]Error analyzing image after {max_retries} attempts: {str(e)}[/red]")
                        return True
                
                console.print("\n[bold]Visual Analysis:[/bold]")
                console.print(image_description)
                
                # Ask user for implementation details
                console.print("\n[bold blue]What would you like to implement based on this design? (Type your request or 'skip' to continue)[/bold blue]")
                console.print("[dim]Example: Create a landing page with similar layout and colors[/dim]")
                user_prompt = Prompt.ask("Your implementation request")
                
                if user_prompt.lower() != 'skip':
                    # Send both image description and user prompt to chat
                    full_prompt = f"""Visual Reference:
{image_description}

Implementation Request: {user_prompt}

Based on the visual reference above and the implementation request, please:
1. Create a detailed plan for implementation
2. Follow the visual style from the reference
3. Include all necessary files and code
4. Add appropriate animations and interactions
5. Ensure responsive design

Respond with actions to create the implementation."""
                    
                    try:
                        response = chat.send_message(full_prompt)
                        console.print("\n[bold]Implementation Plan:[/bold]")
                        console.print(response.text)
                    except Exception as e:
                        console.print(f"[red]Error processing request: {str(e)}[/red]")
                
            except Exception as e:
                console.print(f"[red]Unexpected error: {str(e)}[/red]")
            
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
            projects_dir = os.path.join(self.base_dir, "projects")
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
                    choices=["open", "create", "delete", "exit"]
                )
                
            if action == "exit":
                break
                
            elif action == "delete":
                project = Prompt.ask("Select project to delete", choices=projects)
                if Prompt.ask(f"[red]Are you sure you want to delete '{project}'?[/red]", choices=["y", "n"]) == "y":
                    try:
                        # Delete project directory
                        project_dir = os.path.join(projects_dir, project)
                        import shutil
                        shutil.rmtree(project_dir)
                        
                        # Delete associated chat history
                        chat_file = os.path.join(self.base_dir, "chats", f"chat_{project}.json")
                        if os.path.exists(chat_file):
                            os.remove(chat_file)
                            
                        # Remove from persistent files if exists
                        if project in self.persistent_files:
                            del self.persistent_files[project]
                            
                        console.print(f"[green]Project '{project}' deleted successfully[/green]")
                        continue
                    except Exception as e:
                        console.print(f"[red]Error deleting project: {str(e)}[/red]")
                        continue
                else:
                    continue
            
            elif action == "create":
                project_name = Prompt.ask("Enter project name")
                if project_name in projects:
                    console.print("[red]Project already exists![/red]")
                    continue
                project_dir = os.path.join(projects_dir, project_name)
                os.makedirs(project_dir)
                project = project_name
            else:  # open
                project = Prompt.ask("Select project", choices=projects)
            
            project_dir = os.path.join(projects_dir, project)
            
            # Store current directory to restore later
            original_dir = os.getcwd()
            # Change to project directory for terminal commands
            os.chdir(project_dir)
            
            console.print(f"\n[bold green]Working on project: {project}[/bold green]")
            console.print("Type your request in natural language or 'exit' to quit")
            console.print("You can ask me to run terminal commands!")
            
            # Update system prompt to inform about terminal capabilities
            system_prompt = f"""You are managing the project '{project}' in directory '{project_dir}'.
            You can create, edit, read, move and delete files.
            You can also execute terminal commands in the project directory using the 'terminal' action type.
            When asked to perform terminal operations, respond with appropriate terminal action.
            
            IMPORTANT: Always use 'edit' action_type when modifying existing files, never 'create' for files that already exist.
            
            Always respond with a JSON array of actions when asked to modify the project.
            Example action format:
            [
                {{
                    "action_type": "create",
                    "path": "src/main.py",
                    "content": "print('Hello World')",
                    "description": "Create main.py file with hello world code"
                }},
                {{
                    "action_type": "edit",
                    "path": "src/main.py",
                    "content": "def hello():\\n    print('Hello World')",
                    "description": "Modify main.py to use a function"
                }},
                {{
                    "action_type": "terminal",
                    "content": "npm install express",
                    "description": "Install Express.js dependency"
                }}
            ]"""
            
            # Iniciar chat do projeto com novo system prompt
            chat, chat_file = self.start_project_chat(project, project_dir, model, system_prompt)
            
            try:
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
            
            finally:
                # Restore original directory when exiting project
                os.chdir(original_dir)
    
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
                    try:
                        os.system(action['content'])
                    except Exception as e:
                        console.print(f"[red]Error executing command: {str(e)}[/red]")
                    
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
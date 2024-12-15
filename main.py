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
model = genai.GenerativeModel(
    'gemini-2.0-flash-exp',
    generation_config=genai.GenerationConfig(
        max_output_tokens=8192,
        temperature=0.9,
        top_p=1,
        top_k=1
    )
)

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
        
        # Lista de diretórios a serem ignorados
        ignored_dirs = {
            '__pycache__',
            'venv',
            'env',
            'node_modules',
            '.git',
            '.idea',
            '.vscode',
            'build',
            'dist',
            'site-packages',
            'egg-info',
            '.pytest_cache',
            '.mypy_cache',
            '.tox',
            'coverage',
            'htmlcov',
            '.coverage',
            'vendor',
            'bower_components',
            'jspm_packages',
            'lib',
            'libs',
            'bin',
            'obj',
            'target',
            'out'
        }
        
        for root, dirs, files in os.walk(project_dir):
            # Filtrar diretórios ignorados e ocultos
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ignored_dirs]
            
            for file in files:
                if not file.startswith('.'):
                    # Converter para caminho relativo ao diretório do projeto
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, project_dir)
                    file_paths.append(rel_path)
        
        return sorted(file_paths)

    def start_project_chat(self, project, project_dir, model, system_prompt, chat_name="main"):
        # Criar diretório de chats se não existir
        chats_dir = os.path.join(self.base_dir, "chats", project)
        if not os.path.exists(chats_dir):
            os.makedirs(chats_dir)
        
        # Nome do arquivo de chat baseado no projeto e nome do chat
        chat_file = os.path.join(chats_dir, f"{chat_name}.json")
        
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

    def process_custom_command(self, command, project_dir, chat, project, chat_file=None):
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
/add-image path - Add and analyze local PNG image
/new-chat name  - Create a new chat session
/open-chat name - Open an existing chat session
/remove-chat name - Remove a chat session
/chat-list      - List all available chats
/exit           - Exit current project
/plan           - Create and execute a project iteration plan
/plan-mode      - Enable automatic iteration planning for all requests

[bold]Examples:[/bold]
/codebase find security issues
/add-file src/main.py
/add-folder src/utils
/remove-file config.json
/is-web         # Enable beautiful web UI generation
/add-image designs/mockup.png
/new-chat feature-auth
/open-chat feature-ui
/remove-chat old-feature
/plan
""")
            return True
            
        elif command.startswith('/new-chat'):
            chat_name = command[10:].strip()
            if not chat_name:
                console.print("[red]Please provide a chat name[/red]")
                return True
                
            # Verificar se o chat já existe
            chats_dir = os.path.join(self.base_dir, "chats", project)
            if not os.path.exists(chats_dir):
                os.makedirs(chats_dir)
                
            chat_file = os.path.join(chats_dir, f"{chat_name}.json")
            
            if os.path.exists(chat_file):
                console.print(f"[red]Chat '{chat_name}' already exists[/red]")
                return True
            
            # Criar arquivo de chat vazio
            try:
                with open(chat_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                console.print(f"[green]Created new chat: {chat_name}[/green]")
            except Exception as e:
                console.print(f"[red]Error creating chat: {str(e)}[/red]")
            return True
            
        elif command.startswith('/open-chat'):
            chat_name = command[11:].strip()
            if not chat_name:
                console.print("[red]Please provide a chat name[/red]")
                return True
                
            # Verificar se o chat existe
            chats_dir = os.path.join(self.base_dir, "chats", project)
            chat_file = os.path.join(chats_dir, f"{chat_name}.json")
            
            if not os.path.exists(chat_file):
                console.print(f"[red]Chat '{chat_name}' not found[/red]")
                return True
            
            # Get current system prompt from main chat
            current_system_prompt = chat.history[0].parts[0].text
            
            # Abrir chat existente
            chat, chat_file = self.start_project_chat(project, project_dir, model, current_system_prompt, chat_name)
            console.print(f"[green]Opened chat: {chat_name}[/green]")
            return True
            
        elif command.startswith('/chat-list'):
            # Checar tanto o diretório do projeto quanto o diretório raiz de chats
            chats_dir = os.path.join(self.base_dir, "chats")
            project_chats_dir = os.path.join(chats_dir, project)
            
            # Migrar chat principal se estiver no diretório raiz
            main_chat_file = f"chat_{project}.json"
            main_chat_path = os.path.join(chats_dir, main_chat_file)
            if os.path.exists(main_chat_path):
                # Criar diretório do projeto se não existir
                if not os.path.exists(project_chats_dir):
                    os.makedirs(project_chats_dir)
                # Mover arquivo
                new_path = os.path.join(project_chats_dir, main_chat_file)
                try:
                    os.rename(main_chat_path, new_path)
                    console.print(f"[yellow]Migrated {main_chat_file} to project folder[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error migrating chat: {str(e)}[/red]")
            
            # Listar chats (agora todos estarão na pasta do projeto)
            chats = []
            if os.path.exists(project_chats_dir):
                chats = [os.path.splitext(f)[0] for f in os.listdir(project_chats_dir) if f.endswith('.json')]
            
            if not chats:
                console.print("[yellow]No chats found for this project[/yellow]")
                return True
                
            console.print("\n[bold]Available chats:[/bold]")
            # Mostrar chat principal primeiro (chat_project ou main)
            main_chat = f"chat_{project}"
            if main_chat in chats:
                console.print(f"- {main_chat} [bold cyan](default)[/bold cyan]")
                chats.remove(main_chat)
            elif "main" in chats:
                console.print(f"- main [bold cyan](default)[/bold cyan]")
                chats.remove("main")
            # Mostrar outros chats
            for chat_name in sorted(chats):
                console.print(f"- {chat_name}")
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
            
            # Lista de diretórios a serem ignorados
            ignored_dirs = {
                '__pycache__',
                'venv',
                'env',
                'node_modules',
                '.git',
                '.idea',
                '.vscode',
                'build',
                'dist',
                'site-packages',
                'egg-info',
                '.pytest_cache',
                '.mypy_cache',
                '.tox',
                'coverage',
                'htmlcov',
                '.coverage',
                'vendor',
                'bower_components',
                'jspm_packages',
                'lib',
                'libs',
                'bin',
                'obj',
                'target',
                'out'
            }
            
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
            
            # Listar arquivos no diretório e subdiretórios, ignorando pastas específicas
            for root, dirs, files in os.walk(full_folder_path):
                # Filtrar diretórios ignorados
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ignored_dirs]
                
                for file in files:
                    if not file.startswith('.'):
                        file_path = os.path.join(root, file)
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
            image_path = command[11:].strip()
            if not image_path:
                console.print("[red]Please provide the image path[/red]")
                return True
                
            try:
                # Converter path relativo para absoluto se necessário
                if not os.path.isabs(image_path):
                    image_path = os.path.join(project_dir, image_path)
                
                if not os.path.exists(image_path):
                    console.print(f"[red]Image not found: {image_path}[/red]")
                    return True
                
                if not image_path.lower().endswith('.png'):
                    console.print("[red]Only PNG images are supported[/red]")
                    return True
                
                console.print("[bold blue]Reading image...[/bold blue]")
                
                try:
                    with open(image_path, 'rb') as img_file:
                        image_bytes = img_file.read()
                        import base64
                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        
                        # Criar prompt com a imagem
                        image_prompt = {
                            "role": "user",
                            "parts": [
                                {
                                    "inline_data": {
                                        "mime_type": "image/png",
                                        "data": image_base64
                                    }
                                }
                            ]
                        }
                        
                        # Adicionar imagem ao histórico do chat
                        chat.history.append(image_prompt)
                        console.print("[green]Image added to context. Your next prompt will include the image analysis.[/green]")
                        console.print("[dim]The image will be removed from context after your next prompt.[/dim]")
                        
                except Exception as e:
                    console.print(f"[red]Error reading image: {str(e)}[/red]")
                    return True
                
            except Exception as e:
                console.print(f"[red]Error processing image: {str(e)}[/red]")
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
        
        elif command.startswith('/remove-chat'):
            chat_name = command[12:].strip()
            if not chat_name:
                console.print("[red]Please provide a chat name[/red]")
                return True
                
            # Não permitir remover chats especiais (chat_project ou main)
            if chat_name in ['main', f'chat_{project}']:
                console.print("[red]Cannot remove default chat[/red]")
                return True
                
            # Verificar se o chat existe
            chats_dir = os.path.join(self.base_dir, "chats", project)
            chat_file = os.path.join(chats_dir, f"{chat_name}.json")
            
            if not os.path.exists(chat_file):
                console.print(f"[red]Chat '{chat_name}' not found[/red]")
                return True
            
            # Remover arquivo do chat
            try:
                os.remove(chat_file)
                console.print(f"[green]Removed chat: {chat_name}[/green]")
            except Exception as e:
                console.print(f"[red]Error removing chat: {str(e)}[/red]")
            return True
        
        elif command.startswith('/plan'):
            project_query = command[6:].strip()
            try:
                # Modificar o prompt para enfatizar o uso do diretório raiz
                planning_prompt = f"""Create an iteration plan for the project.
{f'Project requirements: {project_query}' if project_query else 'Analyze the current project state and create a plan for completion.'}

Rules for the plan:
1. Each iteration must have maximum 4 steps
2. Each step should be clear and achievable
3. Steps should be in logical order
4. Each iteration should have a clear goal
5. Consider dependencies between steps
6. Include testing and validation when needed
7. IMPORTANT: All files and directories must be created in the root directory '.'
   - DO NOT create a new project directory inside the project
   - Use relative paths starting with './' or just the filename
   - Example: './src/App.js' or 'package.json', not 'my-app/src/App.js'
   - All commands should run in the current directory
   - For npm/yarn init, use the current directory

Format your response as:
```plan
Iteration 1: [Goal Description]
1. [Step 1]
2. [Step 2]
3. [Step 3]
4. [Step 4]

Iteration 2: [Goal Description]
1. [Step 1]
...
```

Then explain why you chose this order and any important considerations.

Remember: All files and commands must work in the current directory '.' - DO NOT create a new project directory!"""

                response = chat.send_message(planning_prompt)
                plan_text = response.text
                
                # Extrair o plano entre ```plan e ```
                import re
                plan_match = re.search(r'```plan\n(.*?)\n```', plan_text, re.DOTALL)
                if not plan_match:
                    console.print("[red]Could not parse the plan format[/red]")
                    return True
                    
                plan = plan_match.group(1)
                
                # Mostrar o plano e a explicação
                console.print("\n[bold blue]Project Iteration Plan:[/bold blue]")
                console.print(plan)
                
                # Mostrar explicação (texto após o bloco do plano)
                explanation = plan_text.split('```')[-1].strip()
                if explanation:
                    console.print("\n[bold]Plan Explanation:[/bold]")
                    console.print(explanation)
                
                # Perguntar se quer começar as iterações
                if Prompt.ask("\nStart executing iterations?", choices=["y", "n"]) == "y":
                    # Separar iterações
                    iterations = re.findall(r'Iteration \d+:.*?(?=\nIteration \d+:|$)', plan, re.DOTALL)
                    
                    for i, iteration in enumerate(iterations, 1):
                        console.print(f"\n[bold blue]Starting Iteration {i}[/bold blue]")
                        console.print(iteration.strip())
                        
                        if i > 1 and Prompt.ask("\nContinue to next iteration?", choices=["y", "n"]) != "y":
                            break
                        
                        # Extrair os passos da iteração
                        steps = re.findall(r'\d+\.\s*(.*?)(?=\n\d+\.|$)', iteration, re.DOTALL)
                        
                        for j, step in enumerate(steps, 1):
                            console.print(f"\n[bold]Step {j}:[/bold] {step.strip()}")
                            
                            # Criar prompt para executar o passo
                            step_prompt = f"""Current Iteration: {i}
Current Step: {j} - {step.strip()}

Based on this step, please:
1. Analyze what needs to be done
2. Generate necessary actions (file creation, modifications, terminal commands)
3. Ensure all changes are properly tested
4. Consider dependencies from previous steps

Respond with specific actions to implement this step."""

                            if Prompt.ask(f"\nExecute step {j}?", choices=["y", "n"]) == "y":
                                try:
                                    response = chat.send_message(step_prompt)
                                    text = response.text.strip()
                                    
                                    # Procurar por ações JSON na resposta
                                    start = text.find('[')
                                    end = text.rfind(']') + 1
                                    
                                    if start != -1 and end != 0:
                                        actions = json.loads(text[start:end])
                                        
                                        # Mostrar e confirmar ações
                                        console.print("\n[bold]Proposed actions:[/bold]")
                                        for action in actions:
                                            console.print(f"\n- {action['description']}")
                                            if action['action_type'] == 'terminal':
                                                console.print(f"  Command: {action['content']}")
                                        
                                        if Prompt.ask("\nProceed with these actions?", choices=["y", "n"]) == "y":
                                            for action in actions:
                                                self.execute_action(action, chat)
                                    else:
                                        console.print("\n[bold]AI Response:[/bold]")
                                        console.print(text)
                                    
                                except Exception as e:
                                    console.print(f"[red]Error in step {j}: {str(e)}[/red]")
                                    if Prompt.ask("Continue to next step?", choices=["y", "n"]) != "y":
                                        break
                            
                            # Salvar histórico após cada passo
                            if chat_file:
                                self.save_chat_history(chat, chat_file)
                        
                    console.print("\n[bold green]Project plan execution completed![/bold green]")
                
            except Exception as e:
                console.print(f"[red]Error creating/executing plan: {str(e)}[/red]")
            return True
        
        elif command.startswith('/plan-mode'):
            try:
                plan_mode_prompt = """From now on, I will automatically create and follow iteration plans for all project requests.
Each request will be broken down into iterations following these rules:

1. Each iteration must have maximum 4 steps
2. Each step should be clear and achievable
3. Steps should be in logical order
4. Each iteration should have a clear goal
5. Consider dependencies between steps
6. Include testing and validation when needed
7. IMPORTANT: All files and directories must be created in the root directory '.'
   - DO NOT create a new project directory inside the project
   - Use relative paths starting with './' or just the filename
   - Example: './src/App.js' or 'package.json', not 'my-app/src/App.js'
   - All commands should run in the current directory
   - For npm/yarn init, use the current directory

For every request, I will:
1. Create a plan in the specified format
2. Execute each iteration step by step
3. Validate each step before moving to the next
4. Keep all files in the root project directory

Respond with 'PLAN_MODE_ENABLED' if you understand."""

                response = chat.send_message(plan_mode_prompt)
                if "PLAN_MODE_ENABLED" in response.text:
                    console.print("[bold green]Plan mode enabled! All requests will now follow iteration plans automatically.[/bold green]")
                else:
                    console.print("[red]Error enabling plan mode[/red]")
            except Exception as e:
                console.print(f"[red]Error enabling plan mode: {str(e)}[/red]")
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
                        
                        # Delete project chats directory
                        chats_project_dir = os.path.join(self.base_dir, "chats", project)
                        if os.path.exists(chats_project_dir):
                            shutil.rmtree(chats_project_dir)
                            console.print(f"[yellow]Removed project chat history[/yellow]")
                        
                        # Delete legacy chat file if exists (backwards compatibility)
                        legacy_chat_file = os.path.join(self.base_dir, "chats", f"chat_{project}.json")
                        if os.path.exists(legacy_chat_file):
                            os.remove(legacy_chat_file)
                            
                        # Remove from persistent files if exists
                        if project in self.persistent_files:
                            del self.persistent_files[project]
                            
                        console.print(f"[green]Project '{project}' and all associated data deleted successfully[/green]")
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
                        if self.process_custom_command(prompt, project_dir, chat, project, chat_file):
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
                        
                        # Remover imagem do histórico após o prompt se existir
                        if chat.history and len(chat.history) >= 2:
                            previous_msg = chat.history[-2]  # Mensagem anterior à resposta atual
                            if (hasattr(previous_msg, 'parts') and 
                                len(previous_msg.parts) > 0 and 
                                hasattr(previous_msg.parts[0], 'inline_data')):
                                # Remover a mensagem com a imagem
                                chat.history.pop(-2)
                                console.print("[dim]Image removed from context[/dim]")
                        
                        text = response.text.strip()
                        
                        # Procurar por ações JSON na resposta
                        start = text.find('[')
                        end = text.rfind(']') + 1
                        
                        if start != -1 and end != 0:
                            try:
                                actions = json.loads(text[start:end])
                                
                                # Mostrar e confirmar ações
                                console.print("\n[bold]Proposed actions:[/bold]")
                                for action in actions:
                                    console.print(f"\n- {action['description']}")
                                    if action['action_type'] == 'terminal':
                                        console.print(f"  Command: {action['content']}")
                                
                                if Prompt.ask("\nProceed with these actions?", choices=["y", "n"]) == "y":
                                    for action in actions:
                                        self.execute_action(action, chat)
                            except json.JSONDecodeError:
                                # Se não conseguir decodificar como JSON, mostrar resposta normal
                                console.print("\n[bold]AI Response:[/bold]")
                                console.print(text)
                        else:
                            # Se não encontrar ações JSON, mostrar resposta normal
                            console.print("\n[bold]AI Response:[/bold]")
                            console.print(text)
                        
                        # Salvar histórico do chat
                        if chat_file:
                            self.save_chat_history(chat, chat_file)
                        
                    except Exception as e:
                        console.print(f"[red]Error: {str(e)}[/red]")
                
            finally:
                # Restore original directory when exiting project
                os.chdir(original_dir)
    
    def execute_action(self, action, chat):
        try:
            if action['action_type'] == 'create':
                # Validar se o path está vazio ou None
                if not action.get('path') or action['path'].strip() == '':
                    console.print("[red]Error: Invalid or empty file path[/red]")
                    console.print(f"[yellow]Debug - Received path: '{action.get('path')}'[/yellow]")
                    return
                
                # Normalizar o path para evitar problemas com barras
                action['path'] = os.path.normpath(action['path'].strip())
                
                # Validar se o conteúdo existe
                if 'content' not in action or action['content'] is None:
                    console.print("[red]Error: No content provided for file[/red]")
                    return
                
                # Criar diretórios necessários
                file_dir = os.path.dirname(action['path'])
                if file_dir and not os.path.exists(file_dir):
                    try:
                        os.makedirs(file_dir)
                    except Exception as e:
                        console.print(f"[red]Error creating directory {file_dir}: {str(e)}[/red]")
                        return
                
                if Prompt.ask(f"Create {action['path']}?", choices=["y", "n"]) == "y":
                    try:
                        with open(action['path'], 'w', encoding='utf-8') as f:
                            f.write(action['content'])
                        console.print(f"[green]Created {action['path']}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error creating file {action['path']}: {str(e)}[/red]")
                        console.print(f"[yellow]Debug - Path: '{action['path']}'[/yellow]")
                        console.print(f"[yellow]Debug - Content length: {len(action['content'])}[/yellow]")
                    
            elif action['action_type'] == 'edit':
                # Validar se o path está vazio
                if not action.get('path'):
                    console.print("[red]Error: Empty file path provided[/red]")
                    return
                
                if Prompt.ask(f"Edit {action['path']}?", choices=["y", "n"]) == "y":
                    self.file_manager.edit_file(action['path'], action['content'])
                    
            elif action['action_type'] == 'move':
                # Validar paths
                if not action.get('path') or not action.get('content'):
                    console.print("[red]Error: Source or destination path is empty[/red]")
                    return
                
                if Prompt.ask(f"Move {action['path']} to {action['content']}?", choices=["y", "n"]) == "y":
                    # Criar diretório de destino se necessário
                    dest_dir = os.path.dirname(action['content'])
                    if dest_dir and not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    os.rename(action['path'], action['content'])
                    
            elif action['action_type'] == 'remove':
                # Validar se o path está vazio
                if not action.get('path'):
                    console.print("[red]Error: Empty file path provided[/red]")
                    return
                
                if Prompt.ask(f"Remove {action['path']}?", choices=["y", "n"]) == "y":
                    self.file_manager.delete_file(action['path'])
                    
            elif action['action_type'] == 'terminal':
                # Validar se o comando está vazio
                if not action.get('content'):
                    console.print("[red]Error: Empty terminal command[/red]")
                    return
                
                if Prompt.ask(f"Run command: {action['content']}?", choices=["y", "n"]) == "y":
                    try:
                        import signal
                        
                        console.print("[bold blue]Executing command... (Press CTRL+C to stop)[/bold blue]")
                        
                        try:
                            # Executar comando usando os.system
                            exit_code = os.system(action['content'])
                            
                            if exit_code != 0:
                                console.print(f"\n[red]Command failed with exit code: {exit_code}[/red]")
                            
                        except KeyboardInterrupt:
                            console.print("\n[yellow]Command interrupted by user[/yellow]")
                            # Em sistemas Unix, enviar SIGINT para o grupo de processo
                            if os.name != 'nt':
                                os.kill(0, signal.SIGINT)
                        
                        # Análise opcional do resultado
                        if Prompt.ask("\nAnalyze command result?", choices=["y", "n"]) == "y":
                            try:
                                analysis_prompt = f"""Command: {action['content']}
Exit code: {exit_code if 'exit_code' in locals() else 'interrupted'}

Please provide a brief analysis:
1. Success/failure status
2. Suggested next steps"""

                                response = chat.send_message(analysis_prompt)
                                console.print("\n[bold]Analysis:[/bold]")
                                console.print(response.text)
                                
                            except Exception as e:
                                console.print(f"[yellow]Could not analyze result: {str(e)}[/yellow]")
                    
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
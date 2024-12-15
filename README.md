# GemiCoder

An AI-powered project generator and manager using Google's Gemini AI.

## Features
- Create, edit, read and delete files/folders through AI
- Chat history saved locally
- Project management system
- Step-by-step project creation with approval system
- Terminal-based interface
- Persistent file context for better AI understanding
- Smart codebase analysis
- Manual project planning with iterations

## Requirements
- Python 3.8+
- Google Cloud API key

## Installation
1. Clone this repository
```bash
git clone https://github.com/Icarogamer2441/gemiCoder.git
cd gemiCoder
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Create a .env file in the root directory and add your Google API key:
```env
GOOGLE_API_KEY=your_api_key_here
```

## Usage

1. Start the program:
```bash
python main.py
```

2. Main menu options:
- `open` - Open an existing project
- `create` - Create a new project
- `delete` - Delete an existing project
- `exit` - Exit program

3. Project commands:
- `/help` - Show all available commands
- `/codebase` - Show and analyze all project files
- `/codebase query` - Analyze files with specific query
- `/add-file path` - Add file to active context
- `/add-folder [path]` - Add all files from folder
- `/remove-file path` - Remove file from active context
- `/is-web` - Enable enhanced web development mode
- `/add-image path` - Add and analyze local PNG image (supports relative/absolute paths)
- `/new-chat name` - Create a new chat session
- `/open-chat name` - Open an existing chat session
- `/chat-list` - List all available chats
- `/remove-chat name` - Remove a chat session (cannot remove default chat)
- `/plan` - Create and execute a project iteration plan
- `/exit` - Exit current project or chat

4. Planning Features:
```bash
# Create an iteration plan for your project
/plan create a react blog

# The plan will break down the project into:
- Logical iterations
- Maximum 4 steps per iteration
- Clear goals and dependencies
- Testing and validation steps
```

The planning system:
- Breaks down requests into logical iterations
- Maximum 4 steps per iteration
- Creates files in the root project directory
- Validates each step before proceeding
- Maintains proper dependencies between steps
- Includes testing and validation
- Prevents nested project creation

5. Examples:
```bash
# Add single file to context
/add-file src/main.py

# Add all files from current project directory
/add-folder

# Add all files from specific folder
/add-folder src/utils

# Analyze codebase for security issues
/codebase find security issues

# Remove file from context
/remove-file config.json

# Enable beautiful web UI generation
/is-web

# Manage multiple chat sessions
/new-chat feature-auth  # Create new chat for auth feature
/open-chat feature-ui   # Switch to UI development chat
/chat-list             # See all available chats
/remove-chat old-chat  # Remove a chat session

# Create project with planning
/plan create a new express api  # Create plan with iterations

# Analyze image from local path
# Note: Only PNG images are supported
/add-image ../designs/mockup.png    # Relative path
/add-image C:/designs/reference.png # Absolute path

# Exit current project or chat
exit
```

6. Natural language commands:
```bash
# Create new files
Create a Python class for user authentication

# Modify existing files
Add error handling to the login function

# Create web interfaces (after /is-web)
Create a login page with animations
Create a responsive dashboard
Add a contact form with validation

# Run terminal commands
Run the tests for the auth module
```

## Project Structure
```
gemiCoder/
├── main.py           # Main program
├── requirements.txt  # Dependencies
├── .env             # API key configuration
├── modules/         # Program modules
├── projects/        # Your projects
└── chats/          # Chat histories
```

## Notes
- All file operations require user confirmation
- Chat history is saved per project
- Files added to context persist between sessions
- Binary files are automatically ignored
- Planning mode creates files in project root
- Each iteration is validated before proceeding

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
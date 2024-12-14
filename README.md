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
- `/exit` - Exit current project

4. Examples:
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

# Analyze image from local path
# Note: Only PNG images are supported
/add-image ../designs/mockup.png    # Relative path
/add-image C:/designs/reference.png # Absolute path

# Exit current project
/exit
```

5. Natural language commands:
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

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
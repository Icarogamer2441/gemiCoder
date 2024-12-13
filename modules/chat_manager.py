import os
import json
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt

console = Console()

class ChatManager:
    def __init__(self):
        self.chats_dir = "chats"
        self.ensure_chats_directory()
        
    def ensure_chats_directory(self):
        if not os.path.exists(self.chats_dir):
            os.makedirs(self.chats_dir)
            
    def start_chat_session(self, model):
        chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        chat_file = os.path.join(self.chats_dir, f"chat_{chat_id}.json")
        
        chat_history = []
        
        console.print("[bold blue]Chat session started (type 'exit' to end)[/bold blue]")
        
        while True:
            user_input = Prompt.ask("You")
            
            if user_input.lower() == "exit":
                break
                
            chat_history.append({"role": "user", "content": user_input})
            
            response = model.generate_content(user_input)
            console.print(f"[bold green]AI:[/bold green] {response.text}")
            
            chat_history.append({"role": "assistant", "content": response.text})
            
            # Save chat history after each interaction
            with open(chat_file, "w") as f:
                json.dump(chat_history, f, indent=4)
                
        console.print(f"[blue]Chat saved to: {chat_file}[/blue]") 
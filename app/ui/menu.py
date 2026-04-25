"""
Beautiful menu for Datahive
"""

import os
import sys
from typing import Optional

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich import box
from rich.text import Text


class DatahiveMenu:
    """Beautiful menu for Datahive"""
    
    def __init__(self):
        self.console = Console()
    
    def clear_screen(self) -> None:
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_header(self) -> None:
        """Show header"""
        self.clear_screen()
        
        # DATAHIVE ASCII Art (simple block letters)
        ascii_art = """
 ██████   █████  ████████  █████  ██   ██ ██ ██    ██ ███████ 
 ██   ██ ██   ██    ██    ██   ██ ██   ██ ██ ██    ██ ██      
 ██   ██ ███████    ██    ███████ ███████ ██ ██    ██ █████   
 ██   ██ ██   ██    ██    ██   ██ ██   ██ ██  ██  ██  ██      
 ██████  ██   ██    ██    ██   ██ ██   ██ ██   ████   ███████ 
        """
        
        # Center the ASCII art
        centered_art = Align.center(Text(ascii_art, style="bold green"))
        
        # Info content
        text_content = Text()
        text_content.append("\n", style="default")
        text_content.append("DATAHIVE FARM BOT", style="bold white")
        text_content.append("\n", style="default")
        text_content.append("Build: ", style="dim white")
        text_content.append("1.2.0 (Public)", style="bold yellow")
        text_content.append("\n\n")
        text_content.append("Telegram: ", style="bold bright_blue")
        text_content.append("https://t.me/BoRn_SliPPy\n", style="bold cyan")
        text_content.append("GitHub: ", style="bold bright_blue")
        text_content.append("https://github.com/BRN-SLP\n", style="bold cyan")
        
        # Main Panel with dark blue border
        main_panel = Panel(
            Align.center(text_content),
            title="[bold green]SYSTEM ACTIVE[/bold green]",
            subtitle="[italic white]Powered by BRN.SLP[/italic white]",
            box=box.HEAVY,
            border_style="#1E3A5F",  # Dark navy blue
            padding=(1, 2),
            width=60
        )
        
        self.console.print(centered_art)
        self.console.print(Align.center(main_panel))
        self.console.print()

    async def show_menu(self) -> int:
        """Show main menu and get user choice"""
        self.show_header()
        
        # Questionary menu
        # We use a custom style to match the neon aesthetic
        custom_style = questionary.Style([
            ('qmark', 'fg:#673ab7 bold'),       
            ('question', 'bold'),               
            ('answer', 'fg:#f44336 bold'),      
            ('pointer', 'fg:#00ffff bold'),     # Cyan pointer
            ('highlighted', 'fg:#00ffff bold'), # Cyan selection
            ('selected', 'fg:#cc5454'),         
            ('separator', 'fg:#cc5454'),        
            ('instruction', ''),                
            ('text', ''),                       
            ('disabled', 'fg:#858585 italic')   
        ])

        choice = await questionary.select(
            "Select an option:",
            choices=[
                "Login accounts",
                "Farm accounts",
                "Bind Solana Wallets",
                "Execute Missions (Standard)",
                "Deploy Stealth Missions (Anti-Sybil) 🥷",
                "Export stats",
                "Clear proxies",
                "Exit"
            ],
            style=custom_style
        ).unsafe_ask_async()
        
        if choice == "Login accounts":
            return 1
        elif choice == "Farm accounts":
            return 2
        elif choice == "Bind Solana Wallets":
            return 6
        elif choice == "Execute Missions (Standard)":
            return 7
        elif choice == "Deploy Stealth Missions (Anti-Sybil) 🥷":
            return 8
        elif choice == "Export stats":
            return 3
        elif choice == "Clear proxies":
            return 4
        elif choice == "Exit":
            return 5
        return 0

    def show_operation_info(self, operation: str, count: int) -> None:
        """Show operation information"""
        self.clear_screen()
        self.show_header()
        
        text = Text()
        text.append(f"\n{operation}\n", style="bold blue")
        text.append(f"Accounts: {count}", style="bold green")
        
        panel = Panel(
            Align.center(text),
            title=f"[bold green]Running...[/bold green]",
            border_style="green",
            width=60
        )
        self.console.print(Align.center(panel))
        print()


# Global menu instance
_menu_instance: Optional[DatahiveMenu] = None


def get_menu() -> DatahiveMenu:
    """Get global menu instance"""
    global _menu_instance
    if _menu_instance is None:
        _menu_instance = DatahiveMenu()
    return _menu_instance
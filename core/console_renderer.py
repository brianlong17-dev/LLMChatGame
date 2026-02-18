from typing import Union

from agents.base_agent import BaseAgent


class ConsoleRenderer:
    COLORS = {
        "RED": "\033[91m", "GREEN": "\033[92m", "BLUE": "\033[94m",
        "YELLOW": "\033[93m", 
        "MAGENTA": "\033[95m",
        "CYAN": "\033[96m",
        "WHITE": "\033[97m",
        
        "SYS": "\033[1;30m", "RESET": "\033[0m",
        "ITALIC": "\033[3m"
    }

    @classmethod
    def print_turn_header(cls, turn_number: int):
        print(f"\n\n\033[1m[TURN {turn_number}]\033[0m")

    @classmethod
    def print_public_action(cls, speaker: Union[str, BaseAgent], message: str, color_name: str = ""):
        display_name, default_color = ConsoleRenderer.get_name_and_color(speaker)
        final_color = color_name or default_color
        final_color = cls.COLORS[final_color]
        display_name = f"{display_name} :" if display_name else ""
        print(f"{final_color}\033[1m{display_name}\033[0m {final_color}{message}{cls.COLORS['RESET']}")
        
    @classmethod
    def print_private(cls, speaker: Union[str, BaseAgent], message: str, color_name: str = "", print_name = True):
        italic = cls.COLORS["ITALIC"]
        reset = cls.COLORS["RESET"]
        
        display_name, default_color = ConsoleRenderer.get_name_and_color(speaker)
        final_color = color_name or default_color
        final_color = cls.COLORS[final_color]
        display_name = f"[{display_name}] - " if print_name else ""
        
        print(f"{final_color}{italic}{display_name}{message}{reset}")

    @classmethod
    def print_system_private(cls, message: str):
        color = cls.COLORS["SYS"]
        print(f"{color}{message}{cls.COLORS['RESET']}")
    
    @classmethod 
    def get_name_and_color(self, speaker: Union[str, BaseAgent]):
        if isinstance(speaker, str):
            if speaker == "SYSTEM":
                color = "SYS"
            else:
                color = "WHITE"
            display_name = speaker
        else:
            # It's an Agent object
            display_name = speaker.name
            color = speaker.color
        return display_name, color
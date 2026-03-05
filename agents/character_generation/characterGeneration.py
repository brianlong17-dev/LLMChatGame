import random
from concurrent.futures import ThreadPoolExecutor
from typing import List
from pydantic import BaseModel, Field
from agents.character_generation.character_lister import CharacterLister
from agents.player import Debater

# 1. Add this small model so Instructor knows what to return
class CharacterProfile(BaseModel):
    persona: str = Field(description="A detailed, first-person personality description, core beliefs, and debate strategy for this historical figure.")
    speaking_style: str = Field(description="Their speaking style, how they talk, to preserve the charcter from context bleed")

# 2. The Generator Class
class CharacterGenerator:
    
    def __init__(self, game_board, client,  model_name: str, higher_model_name: str = None):
        self.client = client
        self.model_name = model_name
        self.higher_model_name = higher_model_name or model_name
        self.game_board = game_board
        self.character_lister = CharacterLister()
        self.characters = self.character_lister.goats
        self.templates = self.character_lister.templates

    def genericPlayers(self, number_of_players):
        
        debaters = []
        for i in range(number_of_players):
            name, personality, speaking_style = self.templates[i % len(self.templates)]
            debaters.append(
                Debater(
                    name,
                    personality,
                    client=self.client,
                    model_name=self.model_name,
                    higher_model_name=self.higher_model_name,
                    speaking_style = speaking_style
                )
            )
            
        return debaters
    
    def generate_balanced_cast(self, count) -> 'Debater':
        cast = []
        # Shuffle the pools so we don't always start with a 'Regular'
        pools = list(self.character_lister.pools)
        for_sure = list(self.character_lister.for_sure)
        random.shuffle(pools)
        
        for i in range(count):
            if for_sure:
                current_pool = for_sure
            else:
                # Use modulo to loop back to the first pool if count > 5
                current_pool = pools[i % len(pools)]
            
            if current_pool:
                # Pick, remove, and add to cast
                name = random.choice(current_pool)
                current_pool.remove(name)
                if not (name in cast):
                    cast.append(name)
               
        if not cast:
            return []
        with ThreadPoolExecutor(max_workers=min(32, len(cast))) as executor:
            return list(executor.map(self.generate_debater, cast))
       
    def generate_random_debater(self, count) -> 'Debater':
        """Selects a random character from the list and builds a Debater."""
        cast = []
        for _ in range(count):
            character_name = random.choice(self.characters)
            self.characters.remove(character_name) 
            cast.append(character_name)
            self.game_board.system_broadcast(f"Selected: {character_name}...")
        
        if not cast:
            return []
        with ThreadPoolExecutor(max_workers=min(32, len(cast))) as executor:
            return list(executor.map(self.generate_debater, cast))

    def generate_debater(self, character_name: str) -> 'Debater':
        """Calls the LLM to flesh out the character profile and returns a Debater object."""
        
      
        profile = self.client.create(
            model=self.model_name,
            response_model=CharacterProfile,
            messages=[
                {"role": "system", "content": "You are generating a starting profile for an AI debate simulation player."},
                {"role": "user", "content": f"Create a rich, first-person persona and a physical form description for the historical figure: {character_name}. Make them highly opinionated."}
            ]
        )
        self.game_board.system_broadcast(f"Generated: {character_name}. Speaking style: \n {profile.speaking_style}.")
        
        
        # Build and return the Debater using the generated traits
        return Debater(
            name=character_name,
            initial_persona=profile.persona,
            client=self.client,
            model_name=self.model_name,
            higher_model_name=self.higher_model_name,
            speaking_style=profile.speaking_style
        )

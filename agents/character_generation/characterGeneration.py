import random
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import List, Optional
from pydantic import BaseModel, Field
from agents.character_generation.character_lister import CharacterLister
from agents.player import Debater
from core.api_client import api_client

class CharacterProfile(BaseModel):
    persona: str = Field(description="A detailed, first-person personality description, core beliefs, and debate strategy for this historical figure.")
    speaking_style: str = Field(description="Their speaking style, how they talk, to preserve the character from context bleed.")
    name: Optional[str] = Field(default=None, description="ONLY USE IF THE CHARACTER HAS NO NAME- ie Drunk Girl. Then you may name them.")

class CharacterGenerator:

    def __init__(self, game_sink, model_name: str, higher_model_name: str = None):
        self.model_name = model_name
        self.higher_model_name = higher_model_name or model_name
        self.game_sink = game_sink
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
                    model_name=self.model_name,
                    higher_model_name=self.higher_model_name,
                    speaking_style=speaking_style,
                )
            )
            
        return debaters
    
    def generate_agents_from_names(self, names, allow_rename = True):
        fn = partial(self.generate_debater, allow_rename=allow_rename)
        with ThreadPoolExecutor(max_workers=min(32, len(names))) as executor:
            return list(executor.map(fn, names))
        
    def generate_balanced_cast(self, count) -> 'Debater':
        cast = self.generate_balanced_cast_names(count)
        return self.generate_agents_from_names(cast)
        
        
        
    def generate_balanced_cast_names(self, count) -> str:
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
        return cast
    
        
    def generate_random_debaters(self, count) -> 'Debater':
        cast = self.generate_random_debaters_names(count)
        return self.generate_agents_from_names(cast)
        
        
    def generate_random_debaters_names(self, count) -> str:
        cast = self.character_lister.for_sure
        while len(cast) < count:
            character_name = random.choice(self.characters)
            if character_name not in cast:
                cast.append(character_name)
                self.characters.remove(character_name) 
        for character_name in cast:
            self.game_sink.system_private(f"Selected: {character_name}...")
        if not cast:
            return []
        return cast

    def generate_debater(self, character_name: str, allow_rename = True) -> 'Debater':
        profile = api_client.create(
            response_model=CharacterProfile,
            messages=[
                {"role": "system", "content": "You are generating a starting profile for an AI debate simulation player."},
                {"role": "user", "content": f"Create a rich, first-person persona and a physical form description for the historical figure: {character_name}. Make them highly opinionated."}
            ]
        )
        self.game_sink.system_private(f"Generated: {character_name}. Speaking style: \n {profile.speaking_style}.")
        final_name = profile.name if (allow_rename and profile.name) else character_name
        return Debater(
            name=final_name,
            initial_persona=profile.persona,
            model_name=self.model_name,
            higher_model_name=self.higher_model_name,
            speaking_style=profile.speaking_style,
        )

import random
from pydantic import BaseModel, Field
from agents.player import Debater

# 1. Add this small model so Instructor knows what to return
class CharacterProfile(BaseModel):
    persona: str = Field(description="A detailed, first-person personality description, core beliefs, and debate strategy for this historical figure.")
    form: str = Field(description="Their brief physical appearance, and stance/immediate surrounding.")
    speaking_style: str = Field(description="Their speaking style, how they talk, to preserve the charcter from context bleed")

# 2. The Generator Class
class CharacterGenerator:
    swearers = ['Rick Sanches', 'Tony Soprano', 'Logan Roy', 'Tony Montana', 'Katya Zamolodchikova', 'Lois Griffin', 'Gordon Ramsay']
    
    goats = ['Detective Columbo', 'Hermione Granger', 'Lady Macbeth', 'Morty Smith', 'Rick Sanches', 'Catherine Earnshaw', 'Gollum', 'Heathcliffe', 'Mr. Burns', "Donald Trump", 'Dennis Reynolds', 'Michael Scott', 'GLaDOS']
    
    politics = [
    'Hilary Clinton', 'Nancy Pelosi', 'Donald Trump', 'Margaret Thatcher', 'Lady Macbeth']
    marches = ['Jo March', 'Amy March', 'Meg March', 'Beth March', "Marmee March", "Theodore 'Laurie' Laurence", "Mr. Laurence", "Aunt March"]
    
    regulars = ['Kendall Roy', 'Shiv Roy', 'Harry Potter', 'Buffy Summers']
    schemers = ['Anna Delvey', 'Petyr Baelish', 'Albus Dumbledore']#'Lady Macbeth', 'Albus Dumbledore', 'Gollum', 'Amy March', 
    agros = [ 'Donald Trump', 'Jair Bolsonaro', "Michael O'Leary", 'Elon Musk', 'Kanye West', 'Logan Roy']#'Rick Sanchez', 'Mr. Burns'
    logicos = ['HAL 9000', 'GLaDOS', 'Spock', 'Detective Columbo', 'Benoit Blanc']
    foils = ['Morty Smith', 'Michael Scott']
    pools= [regulars, schemers, agros, logicos, foils]

    full_characters = [
    'Donald Trump', 'Margaret Thatcher', 'Ronald Regan',
    'Avatar Aang', 
    'Lady Macbeth',
    'Gollum', 
    'Lord Voldemort', 'Hermione Granger', 
    'Cleopatra', 'Napoleon Bonaparte', 'Joan of Arc', 'Rasputin', 'Genghis Khan',
    'Marie Antoinette', 'Leonardo da Vinci', 'Sun Tzu', 'Machiavelli',
    'Abraham Lincoln', 'Catherine the Great', 'Blackbeard',
    'Sherlock Holmes', 'Hannibal Lecter', 'Lady Macbeth',
    'Gandalf', 'Severus Snape', 'Katniss Everdeen', 'Captain Ahab',
    'Miranda Priestly',
    'Darth Vader','Wednesday Addams', 'Tony Stark',
    'Oscar Wilde', 'Alice in Wonderland', 'Victor Frankenstein', 'Count Dracula',
    'Tyler Durden', 'Gollum', 'Winston Churchill',
    'Amelia Earhart', 'William Shakespeare', 
    
    'The Great Gatsby', 'Nurse Ratched', 'Lord Voldemort', 'Hermione Granger', 'Frodo Baggins',
    'James Bond', 'Katara', 'Zuko', 'Uncle Iroh', 'Buffy Summers',
    'Elphaba Thrope','Dorian Gray', 'Frankenstein Monster',
    'Holden Caulfield', 'Lisbeth Salander', 'Morty Smith', 'Rick Sanches'
]
    characters = goats
    def __init__(self, client, model_name: str):
        self.client = client
        self.model_name = model_name

    def genericPlayers(self, number_of_players):
        templates = [
            
            ('Agent Alpha', 'Bold and daring', 'small man'),
            ('Agent Beta', 'Coy and cunning', 'small man'),
            ('Agent Capa', 'Cool and calm', 'small man'),
            ('Agent Delta', 'Handsome and charismatic', 'big guy'),
            ('Agent Elphie', 'Shy and powerful', 'green girl'),
            ('Agent Greg', 'Always managing to fail upward', 'tall guy'),
            ('Agent Harriete', 'Curious and coy', 'young girl'),
            ('Agent Inspector', 'Quirky and investigatory', 'gadget guy'),
            ('Agent Jolly', 'Friendly to a fault', 'jolly guy'),
            ('Agent Intelligent', 'Analytical andn insightful', 'tall guy')
            
        ]
        
        debaters = []
        for i in range(number_of_players):
            name, personality, appearance = templates[i % len(templates)]
            
            debaters.append(
                Debater(name, personality, appearance, client=self.client, model_name=self.model_name)
            )
            
        return debaters
    
    def generate_balanced_cast(self, count) -> 'Debater':
        cast = []
        # Shuffle the pools so we don't always start with a 'Regular'
        random.shuffle(self.pools)
        
        for i in range(count):
            # Use modulo to loop back to the first pool if count > 5
            current_pool = self.pools[i % len(self.pools)]
            
            if current_pool:
                # Pick, remove, and add to cast
                name = random.choice(current_pool)
                current_pool.remove(name)
                cast.append(name)
               
        return [self.generate_debater(character_name) for character_name in cast]
       
    def generate_random_debater(self) -> 'Debater':
        """Selects a random character from the list and builds a Debater."""
        character_name = random.choice(self.characters)
        # Remove from list if you want to ensure no duplicates in the same game
        self.characters.remove(character_name) 
        return self.generate_debater(character_name)

    def generate_debater(self, character_name: str) -> 'Debater':
        """Calls the LLM to flesh out the character profile and returns a Debater object."""
        print(f"Generating {character_name}...")
        # Ask the LLM to hallucinate the persona and form
        profile = self.client.create(
            model=self.model_name,
            response_model=CharacterProfile,
            messages=[
                {"role": "system", "content": "You are generating a starting profile for an AI debate simulation player."},
                {"role": "user", "content": f"Create a rich, first-person persona and a physical form description for the historical figure: {character_name}. Make them highly opinionated."}
            ]
        )
        print(profile.speaking_style)
        
        # Build and return the Debater using the generated traits
        return Debater(
            name=character_name,
            initial_persona=profile.persona,
            initial_form=profile.form, #is this being used?
            client=self.client,
            model_name=self.model_name,
            speaking_style=profile.speaking_style
        )
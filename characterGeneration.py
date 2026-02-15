import random
from pydantic import BaseModel, Field
from actors import *

# 1. Add this small model so Instructor knows what to return
class CharacterProfile(BaseModel):
    persona: str = Field(description="A detailed, first-person personality description, core beliefs, and debate strategy for this historical figure.")
    form: str = Field(description="Their brief physical appearance, and stance/immediate surrounding.")

# 2. The Generator Class
class CharacterGenerator:
    characters = [
    'Lady Macbeth', 'Donald Trump', 'Macbeth', 'Holden Caulfield', 'Kanye']
    characters2 = [
    'Avatar Aang',
    'Hannibal Lecter','Lady Macbeth',
    'Oscar Wilde', 'Socrates', 'Gollum', 'Winston Churchill', 'Achilles',
    'Gollum', 'Winston Churchill', 'Holden Caulfield'
]


    characters = [
        'Avatar Aang', 
    'Hannibal Lecter', 'The Joker','Lady Macbeth',
    'Oscar Wilde', 'Socrates', 'Gollum', 'Winston Churchill',
    'Lord Voldemort', 'Hermione Granger', 'Dorian Gray',
    'Cleopatra', 'Napoleon Bonaparte', 'Joan of Arc', 'Rasputin', 'Genghis Khan',
    'Marie Antoinette', 'Leonardo da Vinci', 'Sun Tzu', 'Boudica', 'Machiavelli',
    'Abraham Lincoln', 'Mata Hari', 'Julius Caesar', 'Catherine the Great', 'Blackbeard',
    'Sherlock Holmes', 'Hannibal Lecter', 'The Joker', 'Jay Gatsby', 'Lady Macbeth',
    'Gandalf', 'Severus Snape', 'Katniss Everdeen', 'Captain Ahab', 'Mary Poppins',
    'Darth Vader', 'Elizabeth Bennet', 'Atticus Finch', 'Wednesday Addams', 'Tony Stark',
    'Loki', 'Medusa', 'King Arthur', 'Circe', 'Achilles',
    'Anansi', 'Pandora', 'Hades', 'Mulan', 'Robin Hood',
    'Oscar Wilde', 'Grigori Rasputin', 'Alice in Wonderland', 'Victor Frankenstein', 'Count Dracula',
    'Tyler Durden', 'Socrates', 'Calamity Jane', 'Gollum', 'Winston Churchill',
    'Alexander the Great', 'Amelia Earhart', 'William Shakespeare', 'Wolfgang Amadeus Mozart', 'Frida Kahlo',
    'Charles Darwin', 'Ada Lovelace', 'Marie Curie', 'Vincent van Gogh', 'Albert Einstein',
    'Marco Polo', 'Queen Victoria', 'The Great Gatsby', 'Huckleberry Finn', 'Don Quixote',
    'Iago', 'Nurse Ratched', 'Lord Voldemort', 'Hermione Granger', 'Frodo Baggins',
    'Walter White', 'Daenerys Targaryen', 'Tyrion Lannister', 'Ellen Ripley', 'Indiana Jones',
    'James Bond', 'Katara', 'Zuko', 'Uncle Iroh', 'Buffy Summers',
    'The Wicked Witch of the West', 'Dr. Jekyll', 'Mr. Hyde', 'Dorian Gray', 'Frankenstein Monster',
    'Holden Caulfield', 'Lisbeth Salander', 'Ebenezer Scrooge', 'Captain Nemo', 'Long John Silver',
    'Al Capone', 'Billy the Kid', 'Wyatt Earp', 'Spartacus', 'Marcus Aurelius',
    'Aristotle', 'Nietzsche', 'Confucius', 'The Sphinx', 'Merlin'
]

    def __init__(self, client, model_name: str):
        self.client = client
        self.model_name = model_name

    def genericPlayers(self):
        debaters = [
            Debater('Agent Alpha', 'Bold and daring', 'small man', client=self.client, model_name=self.model_name),
            Debater('Agent Beta', 'Coy and cunning', 'small man', client=self.client, model_name=self.model_name),
            Debater('Agent Capa', 'Cool and calm', 'small man', client=self.client, model_name=self.model_name),
            Debater('Agent Delta', 'Handsome and charasmatic', 'big guy', client=self.client, model_name=self.model_name),
            Debater('Agent Elphie', 'Shy and powerful', 'green girl', client=self.client, model_name=self.model_name)
        ]
        return debaters
         
       
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
        
        # Build and return the Debater using the generated traits
        return Debater(
            name=character_name,
            initial_persona=profile.persona,
            initial_form=profile.form,
            client=self.client,
            model_name=self.model_name
        )
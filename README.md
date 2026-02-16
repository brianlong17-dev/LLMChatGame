# 🎭 LLM Chat Game: AI Agent Debate Simulation

What started as an LLM debate scorer, evolved into a survivor style game simulation. This is a framework for a project where I eventually plan to make a group chat style game, where you interact to solved a murder myster. 

It’s basically Reality TV for LLMs. The game mechanics are still in development, but initially- and still for the final rounds- the players overseen by an autonomous **Judge** who gets to decide who awards points, based on his own evolving personality.

## 🚀 What is this?

Built with **Gemini 2.0 Flash** and the **Instructor** library, this project moves away from static "Question/Answer" bots. The goal is for these agents to have:
* **Evolving Brains:** The should move beyond just yapping. I'm working on creating objects that have memory and the ability to modify it.
* **A God Complex:** The Judge isn't just a scoreboard. It's a mutating being- it has powers to change agent forms, silencing them, or add create new players.
* **Summarized History:** A Game Master LLM is here to sumarise rounds to keep the LLMs from getting overwhelmed. This also oversees the game and gives feedback towards its future devlopment.

---

## 🏗️ The Logic

* **`SimulationEngine` (`gameplay.py`)**: The conductor. It handles the loop and triggers the final "kill-or-be-killed" phases.
* **`Judge` & `Debater` (`actors.py`)**: The players. Everyone has a persona, a physical form, and a strategy to win (which they update constantly).
* **`GameBoard` (`gameboard.py`)**: The single source of truth for scores and the current state of the world.
* **`CharacterGenerator` (`characterGeneration.py`)**: The "Soul Factory." It uses LLMs to hallucinate rich, opinionated versions of characters like Gollum, Churchill, or Medusa.
* **`Models` (`models.py`)**: The Pydantic "rules" that keep the LLM output from breaking.

---
## Tech Stack

* **Python >= 3.12**
* **google-genai** (Powered by Gemini models like `gemini-2.0-flash-lite`)
* **instructor** (For structured JSON/Pydantic outputs)
* **pydantic** (Data validation and game state management)
* **python-dotenv** (API key management)

## Getting Started

1. Clone the repo.
2. Install the dependencies (I recommend setting up a virtual environment):
   ```bash
   pip install instructor google-genai python-dotenv pydantic
   ```
3. Create a `.env` file in the root directory and add your Gemini API key:
   ```env
   GEMINI_API_KEY="your_api_key_here"
   ```
4. Run the simulation:
   ```bash
   python gameplay.py
   ```

## Output

The game runs directly in the terminal with colored text to separate the internal monologues, public actions, and System/Judge announcements. At the end of a session, it exports a full Markdown transcript of the debate to an `/output` folder so you can read the whole chaotic story.
# LLM Reality Game Simulation

What started as an LLM debate scorer evolved into a Survivor-style elimination game simulation. LLM agents compete through discussion rounds, mini-games, and voting eliminations — with evolving personas, strategies, and memory — until one winner remains.

Built with **Gemini 2.0 Flash** and the **Instructor** library for structured outputs.

---

## What it does

Agents are more than static Q&A bots. Each agent has:

- **Evolving state** — persona, strategy, speaking style, and life lessons that update after every turn
- **Memory compression** — at the end of each phase, agents summarise what happened into detailed and brief memories, preventing context from growing unboundedly across a long game
- **Visibility-filtered context** — private conversations are only shown to the agents who were part of them
- **A Game Master** — a separate LLM agent that summarises rounds and can select players by personality parameter (e.g. "most chaotic") for wildcard immunity

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full breakdown of how the components fit together.

---

## Tech stack

- Python >= 3.12
- [google-genai](https://pypi.org/project/google-genai/) — Gemini models
- [instructor](https://github.com/jxnl/instructor) — structured Pydantic outputs from LLMs
- [pydantic](https://docs.pydantic.dev/) — data validation and dynamic model generation
- [python-dotenv](https://pypi.org/project/python-dotenv/) — API key management

---

## Getting started

1. Clone the repo.
2. Set up a virtual environment and install dependencies:
   ```bash
   pip install instructor google-genai python-dotenv pydantic
   ```
3. Create a `.env` file in the root with your Gemini API key:
   ```env
   GEMINI_API_KEY="your_api_key_here"
   ```
4. Run the simulation:
   ```bash
   python main.py
   ```

---

## Output

The game runs in the terminal with colored text separating public dialogue, private thoughts, host announcements, and system messages. Agent turns are optionally logged to JSONL files in `logs/` for debugging and analysis — use `read_log.py` to inspect them.

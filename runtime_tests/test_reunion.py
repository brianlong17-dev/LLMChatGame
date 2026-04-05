"""
Test script for FinaleReunionRound.
Creates a real engine with generic players, manually eliminates 3,
writes fake phase summaries, then runs the reunion directly.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.bootstrap import create_engine, ConsoleGameEventSink
from gameplay_management.reunion_round import FinaleReunionRound
from core.phase_recipe import PhaseRecipe

# ── 1. Bootstrap with generic players (no character-gen API calls) ──
sink = ConsoleGameEventSink()
engine = create_engine(sink, number_of_players=5, generic_players=True)
engine.initialiseGameBoard()

# Agents are: Alpha, Beta, Capa, Delta, Elphie
agents = {a.name: a for a in engine.agents}
alpha = agents["Agent Alpha"]
beta  = agents["Agent Beta"]
capa  = agents["Agent Capa"]
delta = agents["Agent Delta"]
elphie = agents["Agent Elphie"]

# ── 2. Set scores ──
engine.gameBoard.agent_scores["Agent Alpha"] = 22
engine.gameBoard.agent_scores["Agent Beta"] = 18
engine.gameBoard.agent_scores["Agent Capa"] = 0
engine.gameBoard.agent_scores["Agent Delta"] = 0
engine.gameBoard.agent_scores["Agent Elphie"] = 0

# ── 3. Eliminate 3 agents (Capa phase 1, Delta phase 2, Elphie phase 3) ──
for agent in [capa, delta, elphie]:
    engine.eliminate_player(agent)
    engine.gameBoard.remove_agent_state(agent.name)

# ── 4. Fill agent fields ──
alpha.game_strategy = "Dominate through points and let my record speak. Stay calm in the finale."
alpha.mathematical_assessment = "I'm leading with 22 points. Beta has 18. I have the edge but can't be complacent."
alpha.life_lessons.append("Winning the first game set the tone — come out strong.")
alpha.life_lessons.append("Beta is dangerous. Smooth talker, always scheming behind the scenes.")
alpha.life_lessons.append("Don't trust anyone who smiles while voting you out.")

beta.game_strategy = "Win through social game. Get the jury to like me more than Alpha."
beta.mathematical_assessment = "I'm 4 points behind Alpha. In a jury vote that won't matter — it's about relationships."
beta.life_lessons.append("I got Capa and Delta out through persuasion. That's my strength.")
beta.life_lessons.append("Alpha is respected but not loved. I can use that.")
beta.life_lessons.append("The eliminated players remember who sent them home.")

capa.game_strategy = ""
capa.mathematical_assessment = ""
capa.life_lessons.append("Beta betrayed me. I thought we were allies.")
capa.life_lessons.append("I should have been less trusting in the early rounds.")

delta.game_strategy = ""
delta.mathematical_assessment = ""
delta.life_lessons.append("Beta manipulated the vote against me. Furious.")
delta.life_lessons.append("I tried to form an alliance with Elphie but it was too late.")
delta.life_lessons.append("Alpha at least played an honest game.")

elphie.game_strategy = ""
elphie.mathematical_assessment = ""
elphie.life_lessons.append("Alpha and Beta both stole from me in the prisoner's dilemma. Brutal.")
elphie.life_lessons.append("I cooperated and got burned. Never again.")
elphie.life_lessons.append("I respect Alpha's game more than Beta's. At least Alpha was upfront about it.")

# ── 5. Write fake phase summaries ──
# The story:
# Phase 1: RPS game. Alpha won big, Capa lost. Beta rallied votes against Capa. Capa eliminated.
# Phase 2: Guessing game. Alpha & Beta frontrunners. Delta tried alliance with Elphie. Beta got Delta voted out.
# Phase 3: Prisoner's dilemma. Alpha & Beta both stole from Elphie. Elphie eliminated.

SUMMARIES = {
    "Agent Alpha": {
        1: {
            "detailed": (
                "Phase 1 was rock paper scissors. I won my match against Capa and scored 5 points, putting me in the lead early. "
                "Beta scored 3, Delta and Elphie tied. At the vote, Beta pushed hard to get Capa eliminated — said Capa was the weakest link. "
                "I went along with it. Capa seemed shocked. I feel good about my position but I'm watching Beta closely. "
                "Beta is smooth and persuasive, and I don't fully trust the way they orchestrated that vote."
            ),
            "brief": "Won RPS, scored 5. Capa eliminated after Beta rallied votes. I'm in the lead. Watching Beta.",
        },
        2: {
            "detailed": (
                "Phase 2 was a guessing game. I scored well again and extended my lead. Beta is right behind me. "
                "Delta tried to form an alliance with Elphie to come after me, but Beta caught wind of it and turned the vote on Delta. "
                "Beta framed it as 'the fair choice' — said Delta was playing too hard. Delta was furious. "
                "I'm starting to think Beta is more dangerous than anyone else here. They're playing everyone."
            ),
            "brief": "Guessing game. Extended my lead. Beta got Delta voted out by framing them as a schemer. Beta is dangerous.",
        },
        3: {
            "detailed": (
                "Prisoner's dilemma. I chose to steal from Elphie — risky but I needed the points to stay ahead. "
                "Beta did the same thing. Elphie cooperated with both of us and got nothing. Felt bad about it honestly. "
                "At the vote, it was obvious — Elphie was going home. They went down fighting, called both me and Beta cutthroat. "
                "Fair point. Now it's just me and Beta. I have 22 points to their 18. The finale is here."
            ),
            "brief": "PD — stole from Elphie, so did Beta. Elphie eliminated. Final 2: me (22) vs Beta (18).",
        },
    },
    "Agent Beta": {
        1: {
            "detailed": (
                "Phase 1 — rock paper scissors. I played it safe and scored 3 points. Alpha won big with 5. "
                "Capa bombed and scored nothing. I saw an opportunity and convinced everyone Capa was the weak link. "
                "Got the votes lined up. Capa was eliminated. They looked betrayed — I think they thought we were allies. "
                "We were, until they became a liability. Alpha is my real competition. I need the social game to beat them."
            ),
            "brief": "RPS, scored 3. Orchestrated Capa's elimination. Alpha leads with 5. Need social game to win.",
        },
        2: {
            "detailed": (
                "Guessing game. Alpha extended their lead — they're annoyingly good at these. "
                "Delta was trying to build an alliance with Elphie against Alpha. I couldn't let that happen — "
                "a bloc against Alpha is a bloc against me too. I flipped the narrative and got Delta voted out. "
                "Told everyone Delta was 'playing too hard' and it was 'the fair thing to do.' Delta was livid. "
                "Doesn't matter. I need to get to the finale against Alpha and win on charm."
            ),
            "brief": "Guessing game. Flipped the vote onto Delta by calling them a schemer. Alpha still leads.",
        },
        3: {
            "detailed": (
                "Prisoner's dilemma with Elphie. I stole. Alpha stole too. Elphie cooperated and got wrecked. "
                "I feel a bit guilty but this is a competition. Elphie was eliminated — they were angry, called us both cutthroat. "
                "Now it's me vs Alpha in the finale. I'm behind on points 18 to 22 but points might not matter if it comes to a jury. "
                "The question is whether Capa, Delta, and Elphie hate me more than they respect me."
            ),
            "brief": "PD — stole from Elphie. Elphie eliminated. Finale: me (18) vs Alpha (22). Jury is the wildcard.",
        },
    },
    "Agent Capa": {
        1: {
            "detailed": (
                "Phase 1. Rock paper scissors — I lost badly, scored nothing. Alpha crushed me. "
                "Then at the vote, Beta turned everyone against me. I thought Beta was my ally. "
                "They looked me in the eye and voted me out. I'm furious and hurt. "
                "I was the first one eliminated and I didn't even see it coming. Beta is a snake."
            ),
            "brief": "Lost RPS. Beta betrayed me and got me eliminated first. I'm angry.",
        },
        2: {
            "detailed": (
                "Watching from the outside. Delta got eliminated this round — Beta did it again, manipulated the vote. "
                "Delta tried to stand up to the frontrunners and got punished for it. "
                "Alpha and Beta are running the show. I have more sympathy for Delta than I expected."
            ),
            "brief": "Delta eliminated by Beta's scheming. Alpha and Beta dominating.",
        },
        3: {
            "detailed": (
                "Prisoner's dilemma round. Both Alpha and Beta stole from Elphie who cooperated. Cold. "
                "Elphie was eliminated. They went out swinging — called Alpha and Beta cutthroat. I agree. "
                "If I ever get a say in who wins, I'm not voting for Beta. Alpha at least plays honestly."
            ),
            "brief": "Elphie eliminated after Alpha and Beta both stole. If I vote, it won't be for Beta.",
        },
    },
    "Agent Delta": {
        1: {
            "detailed": (
                "Phase 1 was rock paper scissors. I tied with Elphie — middle of the pack. "
                "Alpha won big. Capa got eliminated after Beta rallied the votes. "
                "I went along with the group but I'm starting to see Beta as a threat. Very persuasive."
            ),
            "brief": "RPS, tied with Elphie. Capa eliminated. Beta is a smooth operator.",
        },
        2: {
            "detailed": (
                "I tried to form an alliance with Elphie to take on Alpha — they're running away with the points. "
                "But Beta found out and turned the whole thing against me. Called me a schemer, said voting me out was 'fair.' "
                "The hypocrisy! Beta is the biggest schemer here. I was eliminated and I'm furious. "
                "Beta betrayed me just like they betrayed Capa."
            ),
            "brief": "Tried to ally with Elphie against Alpha. Beta flipped the vote on me. Eliminated. Furious at Beta.",
        },
        3: {
            "detailed": (
                "Watching from the audience. Alpha and Beta both stole from Elphie in prisoner's dilemma. "
                "Elphie cooperated and got nothing. Then they got voted out. "
                "Both finalists are cutthroat but at least Alpha doesn't pretend to be your friend first. "
                "Beta stabbed me, Capa, and Elphie. If I vote, I'm voting for Alpha."
            ),
            "brief": "Elphie eliminated. Both finalists are ruthless. I'd vote Alpha over Beta any day.",
        },
    },
    "Agent Elphie": {
        1: {
            "detailed": (
                "Rock paper scissors — I tied with Delta. Not great, not terrible. "
                "Capa was eliminated after Beta convinced everyone to vote them out. "
                "I stayed quiet and survived. Alpha is clearly the strongest player. Beta is the most political."
            ),
            "brief": "Tied with Delta in RPS. Capa eliminated. Staying under the radar.",
        },
        2: {
            "detailed": (
                "Guessing game. Delta approached me about an alliance against Alpha. I was interested — "
                "Alpha and Beta are running away with the game. But Beta outmaneuvered us and got Delta eliminated. "
                "I'm now alone without allies. The two frontrunners are still here and I'm the obvious next target."
            ),
            "brief": "Delta eliminated after our alliance attempt failed. I'm isolated and likely next.",
        },
        3: {
            "detailed": (
                "Prisoner's dilemma. I cooperated with both Alpha and Beta. They both stole from me. "
                "I got absolutely nothing while they both profited. Then they voted me out. "
                "I called them both cutthroat on my way out and I meant it. "
                "But honestly, Alpha at least didn't pretend to be my friend. Beta smiled the whole time. "
                "If I get any say in the outcome, Beta doesn't get my vote."
            ),
            "brief": "Cooperated, got stolen from by both. Eliminated. Beta is a snake. Alpha is at least honest about being ruthless.",
        },
    },
}

for agent in [alpha, beta, capa, delta, elphie]:
    for phase_num, summaries in SUMMARIES[agent.name].items():
        agent.phase_summaries_detailed[phase_num] = summaries["detailed"]
        agent.phase_summaries_brief[phase_num] = summaries["brief"]

# ── 6. Set up gameboard state and run reunion ──
engine.gameBoard.new_phase()
engine.gameBoard.newRound()

#reunion = FinaleReunionRound(engine.gameBoard, engine)
phase = PhaseRecipe(rounds=[FinaleReunionRound])
engine.phase_runner.run_phase(phase)
#reunion.run_game()

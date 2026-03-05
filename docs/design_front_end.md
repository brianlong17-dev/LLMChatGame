Visual Language — Swan Hatch / Apple III
The screen should feel like a CRT monitor from 1980. The background is near-black with a very subtle green or amber tint — not pure black. Text renders in a phosphor green or warm amber, with a soft glow/bloom effect on bright elements. Monospace font throughout, slightly wider tracking than a modern terminal. A gentle scanline overlay across the whole UI — subtle, not distracting, just enough to feel physical. Cursor blink on any active element. The whole thing should look like it's been running in an underground bunker for three years.
Beyond green — amber is the natural second colour, used for warnings, summaries, HOST messages. A dim red for eliminations and system alerts. Otherwise restrained — the palette is small and intentional, not colourful.

Toggles — three states
Bottom toolbar has three toggle switches, styled as chunky physical-looking buttons:

Public only — default, clean feed of agent speech and host messages
+ Thoughts — adds private thoughts into the feed, italic, slightly dimmed green
+ Inner Workings — adds all internal fields (strategy, mathematical assessment etc), further dimmed, clearly subordinate. This is the under-the-hood developer view.


Player Panel — right sidebar
Two sections, separated by a ruled line:
ACTIVE — ranked scoreboard, name in player colour (within the phosphor palette), score, crown on leader.
ELIMINATED — same list treatment but dimmed, struck-through names, shown below a separator. Graveyard energy. Never disappears — the list of the dead grows as the game progresses.

Phase pagination
The feed is not a continuous scroll — each phase renders to its own "page." At the end of a phase the feed stops and waits. Two arrow buttons at the bottom — back and forward — to navigate through past phases like chapters.
Bottom toolbar also has an AUTOPLAY toggle — when off, the game pauses at the end of each phase and waits for you to press the forward arrow to continue. When on, it advances automatically. Default is off, so you read at your own pace.
The page transition itself should feel period-appropriate — a quick screen wipe or a flicker, like the CRT redrawing.



Event mapping to UI

on_game_intro — full-width splash message in the feed before the panel split appears, or a styled banner at the top of the feed
on_phase_header — a visual divider in the feed, e.g. a full-width ruled line with the phase number centred
on_phase_intro — host text appears in feed as a HOST message; summary text appears as a collapsible/dimmed block below it
on_round_start — right panel scoreboard refreshes; a subtle round header injected into the feed
on_round_summary — appears in the feed in amber/yellow, clearly marked SUMMARY, visually distinct from agent speech
on_public_action — main feed entry, speaker name in their color
on_private_thought — feed entry, italic, clearly subordinate — could be toggled on/off
on_turn_header — thin ruled separator in the feed
on_game_over — full-width celebratory banner in the feed
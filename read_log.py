#!/usr/bin/env python3
"""
Usage:
    python read_log.py                                                   # most recent log of any agent
    python read_log.py --agent GLaDOS                                    # most recent log for GLaDOS
    python read_log.py --agent GLaDOS --run 2                            # second most recent for GLaDOS
    python read_log.py logs/GLaDOS_20260319_140000.jsonl                 # specific file
    python read_log.py --all                                             # all response fields
    python read_log.py --prompts                                         # show field prompts too
    python read_log.py --brief                                           # response only, no system/user context
    python read_log.py --brief --all                                     # all response fields, no context
"""

import json
import os
import sys
import argparse

# Terminal colours
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[96m"
YELLOW  = "\033[93m"
GREEN   = "\033[92m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"
BLUE    = "\033[94m"


def divider(label: str, color: str = CYAN) -> None:
    width = 80
    pad = max(0, width - len(label) - 4)
    print(f"\n{color}{BOLD}── {label} {'─' * pad}{RESET}")


def field(label: str, value: str, color: str = WHITE) -> None:
    print(f"{DIM}{label}:{RESET}")
    print(f"{color}{value}{RESET}")
    print()


def render_entry(entry: dict, show_all: bool, show_prompts: bool, brief: bool) -> None:
    call_num  = entry.get("call", "?")
    timestamp = entry.get("timestamp", "")
    agent     = entry.get("agent", "?")
    model     = entry.get("model", "?")

    divider(f"CALL {call_num}  ·  {agent}  ·  {model}  ·  {timestamp}", CYAN)

    if not brief:
        system_prompt = entry.get("system_prompt", "")
        if system_prompt:
            divider("SYSTEM PROMPT", YELLOW)
            field("", system_prompt, DIM)

        user_prompt = entry.get("user_prompt", "")
        if user_prompt:
            divider("USER PROMPT", MAGENTA)
            field("", user_prompt, WHITE)

    field_prompts = entry.get("field_prompts", {})
    if show_prompts and field_prompts:
        divider("FIELD PROMPTS", BLUE)
        for fname, fdesc in field_prompts.items():
            if fdesc:
                field(fname, fdesc, DIM)

    response = entry.get("response", {})
    if isinstance(response, dict):
        divider("RESPONSE", GREEN)
        if show_all:
            for key, value in response.items():
                field(key, str(value) if value is not None else "(empty)", WHITE)
        else:
            pub = response.get("public_response")
            if pub is not None:
                field("public_response", str(pub), WHITE)
    else:
        divider("RESPONSE", GREEN)
        field("", str(response), WHITE)


def find_log(log_dir: str = "logs", agent_name: str = None, run: int = 1) -> str | None:
    """Return the nth most recent log file (run=1 is most recent, run=2 is second most recent, etc.)"""
    if not os.path.isdir(log_dir):
        return None
    prefix = f"{agent_name}_" if agent_name else ""
    candidates = sorted(
        [
            os.path.join(log_dir, f)
            for f in os.listdir(log_dir)
            if f.startswith(prefix) and f.endswith(".jsonl")
        ],
        key=os.path.getmtime,
        reverse=True,  # most recent first
    )
    if not candidates:
        return None
    index = run - 1
    if index >= len(candidates):
        return None, len(candidates)
    return candidates[index], len(candidates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pretty-print a JSONL agent log file.")
    parser.add_argument("logfile", nargs="?", default=None,
                        help="Path to the .jsonl log file (optional)")
    parser.add_argument("--agent", default=None, metavar="NAME",
                        help="Agent name — finds logs for that agent in logs/")
    parser.add_argument("--run", type=int, default=1, metavar="N",
                        help="Which run to show — 1 is most recent (default), 2 is second most recent, etc.")
    parser.add_argument("--all", action="store_true", dest="show_all",
                        help="Show all response fields, not just public_response")
    parser.add_argument("--prompts", action="store_true", dest="show_prompts",
                        help="Show field prompts (what the model was asked for each field)")
    parser.add_argument("--brief", action="store_true", dest="brief",
                        help="Show response only — skip system prompt and user prompt")
    args = parser.parse_args()

    logfile = args.logfile
    if logfile is None:
        result = find_log(agent_name=args.agent, run=args.run)
        logfile, total = result if isinstance(result, tuple) else (result, 0)

        if logfile is None:
            if args.agent:
                if total:
                    print(f"Only {total} log file(s) for '{args.agent}' — can't get run {args.run}.")
                else:
                    print(f"No log files found for agent '{args.agent}' in logs/")
            else:
                print("No .jsonl files found in logs/")
            sys.exit(1)

        agent_label = f"for '{args.agent}'" if args.agent else "overall"
        run_label = f"run {args.run}" if args.run > 1 else "most recent"
        print(f"{DIM}Using {run_label} {agent_label}: {logfile}{RESET}")

    try:
        with open(logfile, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print(f"File not found: {logfile}")
        sys.exit(1)

    if not lines:
        print("Log file is empty.")
        sys.exit(0)

    print(f"\n{BOLD}{CYAN}Log: {logfile}  ({len(lines)} call{'s' if len(lines) != 1 else ''}){RESET}")

    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"{YELLOW}Could not parse line: {e}{RESET}")
            continue
        render_entry(entry, show_all=args.show_all, show_prompts=args.show_prompts, brief=args.brief)

    print(f"\n{DIM}{'─' * 80}{RESET}\n")


if __name__ == "__main__":
    main()
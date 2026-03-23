import json
import os
from abc import abstractmethod
from datetime import datetime, timezone


class BaseAgent:
    def __init__(self, name: str, client, model_name: str, higher_model_name: str = None, color = "BLUE"):
        self.name = name
        self.client = client
        self.model_name = model_name
        self.higher_model_name = higher_model_name or model_name
        self.color = color
        self.use_higher_model = False
        self.debug_log = False          # set to True on any agent to enable logging
        self._log_call_index = 0        # monotonic counter per agent instance
        self._log_path = None           # set on first write, reused within a run

    def lazy_responses(self):
        return {"", "none", " ", "n/a", "not applicable", "nothing", "no lesson"}
    
    _NO_CHANGE_PHRASES = {
        "no change",
        "no changes",
        "no changes are necessary",
        "no changes needed",
        "unchanged",
        "remains unchanged",
        "remains the same",
        "stays the same",
        "no update",
        "no updates",
        "no update needed",
        "not applicable",
        "n/a",
        "none",
        "nothing",
        "no lesson",
        "perfection",
        "is perfection",
        "already perfect",
    }
 
    def _check_if_empty(self, text: str):
        if not text:
            return True
        clean_text = text.strip().rstrip('.').lower()
        if clean_text in self.lazy_responses():
            return True
        # Catch "no change" commentary — check both exact match and containment
        # for short values (under 80 chars) to avoid false positives on long text.
        if len(clean_text) < 80:
            for phrase in self._NO_CHANGE_PHRASES:
                if phrase in clean_text:
                    return True
        return False

    @abstractmethod
    def _system_prompt(self, gameBoard):
        raise NotImplementedError("Subclasses must implement _system_prompt!")
    
    def is_human(self):
        return False

    # ------------------------------------------------------------------
    # Debug logging
    # ------------------------------------------------------------------
    def _log_dir(self) -> str:
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(here)
        return os.path.join(root, "logs")

    def _init_log_file(self) -> str:
        """Create a timestamped log file for this run, pruning old ones if needed."""
        log_dir = self._log_dir()
        os.makedirs(log_dir, exist_ok=True)

        # Collect existing logs for this agent, oldest first
        prefix = f"{self.name}_"
        existing = sorted(
            f for f in os.listdir(log_dir)
            if f.startswith(prefix) and f.endswith(".jsonl")
        )

        # Delete oldest until we're under the cap
        cap = 7
        while len(existing) >= cap:
            os.remove(os.path.join(log_dir, existing.pop(0)))

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}_{timestamp}.jsonl"
        return os.path.join(log_dir, filename)

    def _extract_field_descriptions(self, response_model) -> dict:
        return {
            name: (field.description or "")
            for name, field in response_model.model_fields.items()
        }
    
    def _write_log_entry(self, response_model, api_model: str, messages: list, response) -> None:
        # Create the file on the first call of this run
        if self._log_path is None:
            self._log_path = self._init_log_file()

        try:
            response_dict = response.model_dump()
        except AttributeError:
            response_dict = str(response)

        entry = {
            "call": self._log_call_index,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": self.name,
            "model": api_model,
            "system_prompt": messages[0]["content"],
            "user_prompt": messages[1]["content"],
            "field_prompts": self._extract_field_descriptions(response_model),
            "response": response_dict,
        }

        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    # Core API call
    # ------------------------------------------------------------------
    def get_response(self, user_content: str, response_model, gameBoard, system_content: str = None):

        if system_content is None:
            system_content = self._system_prompt(gameBoard)

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user",   "content": user_content},
        ]

        if self.use_higher_model:
            api_model = self.higher_model_name
            self.use_higher_model = False
        else:
            api_model = self.model_name

        response = self.client.create(
            model=api_model,
            response_model=response_model,
            messages=messages,
        )

        if self.debug_log:
            self._log_call_index += 1
            self._write_log_entry(response_model, api_model, messages, response)

        return response
    
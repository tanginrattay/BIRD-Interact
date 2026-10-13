"""Offline checks of the simulator pipeline against Lite task records."""

import ast
import json
import re
import unittest
from pathlib import Path
from typing import Any, Dict, List
from types import SimpleNamespace
from user_simulator.bailian import is_qwen_simulator


ROOT = Path(__file__).resolve().parent.parent
source = (ROOT / "user_simulator" / "server.py").read_text()
nodes = ast.parse(source).body
selected = [node for node in nodes if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and node.name in {"TaskSimState", "_extract_output", "_parse_action",
                              "_generate_response", "_ask_sync", "_ask_direct"}]
namespace = {"json": json, "re": re, "Any": Any, "Dict": Dict, "List": List,
             "segment_sql": lambda sql: [("SQL", sql)],
             "logger": type("Logger", (), {"info": lambda *args: None})(),
             "is_qwen_simulator": is_qwen_simulator,
             "settings": SimpleNamespace(user_sim_model="moonshot/kimi-k2.6", user_sim_pipeline="auto")}
prompts = {}
exec((ROOT / "user_simulator" / "prompts.py").read_text(), prompts)
namespace.update(prompts)
namespace["PROMPT_VERSION"] = "v2"
exec(compile(ast.Module(body=selected, type_ignores=[]), str(ROOT / "user_simulator" / "server.py"), "exec"), namespace)


class UserSimulatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "bird-interact-lite" / "bird_interact_data.jsonl").open() as data:
            cls.tasks = {item["instance_id"]: item for item in map(json.loads, data)
                         if item["instance_id"] in {"alien_1", "alien_2", "alien_3"}}

    def test_real_task_context_and_plain_responses(self):
        cases = [
            ("alien_1", "Does atmospheric conditions mean weather or seeing quality?", "weather conditions"),
            ("alien_2", "What do you mean by BFR measure?", "Bandwidth-to-Frequency Ratio"),
            ("alien_3", "What are problematic events?", "high lunar interference events"),
        ]
        for task_id, question, answer in cases:
            with self.subTest(task_id=task_id):
                task = self.tasks[task_id]
                state = namespace["TaskSimState"](task)
                prompts_seen = []

                def fake_llm(prompt, max_tokens=200):
                    prompts_seen.append(prompt)
                    return "labeled(\"" + task["user_query_ambiguity"]["critical_ambiguity"][0]["term"] + "\")" if len(prompts_seen) == 1 else answer

                namespace["_call_llm"] = fake_llm
                history = [{"role": "agent", "content": "Earlier question"},
                           {"role": "user", "content": "Earlier answer"}]
                action = namespace["_parse_action"](state, question, history)
                response = namespace["_generate_response"](state, question, action, history)
                self.assertEqual(response, answer)
                self.assertEqual(len(prompts_seen), 2)
                for prompt in prompts_seen:
                    self.assertIn(question, prompt)
                    self.assertIn(task["user_query_ambiguity"]["critical_ambiguity"][0]["term"], prompt)
                    reference_sql = task["sol_sql"]
                    if isinstance(reference_sql, list):
                        reference_sql = reference_sql[0]
                    self.assertIn(reference_sql[:40], prompt)
                    self.assertIn("Earlier answer", prompt)
                self.assertIn(task["query"], prompts_seen[1])

    def test_tagged_and_plain_output(self):
        extract = namespace["_extract_output"]
        self.assertEqual(extract("<s>Weather conditions.</s>"), "Weather conditions.")
        self.assertEqual(extract("Weather conditions."), "Weather conditions.")
        self.assertEqual(extract("<think>private reasoning</think>\n<s>Weather.</s>"), "Weather.")

    def test_kimi_direct_prompt_uses_hidden_intent(self):
        task = self.tasks["alien_1"]
        prompts_seen = []

        def fake_llm(prompt, max_tokens=200, reasoning_effort=None, system_prompt=None):
            self.assertIn("Correct any false premise", system_prompt)
            prompts_seen.append((prompt, max_tokens, reasoning_effort))
            return "I mean weather conditions."

        namespace["_call_llm"] = fake_llm
        answer = namespace["_ask_sync"](
            namespace["TaskSimState"](task), "What are atmospheric conditions?")
        self.assertEqual(answer, "I mean weather conditions.")
        prompt, max_tokens, effort = prompts_seen[0]
        self.assertIn(task["query"], prompt)
        self.assertIn(task["amb_user_query"], prompt)
        self.assertIn("WeathProfile", prompt)
        self.assertEqual((max_tokens, effort), (1024, "none"))


if __name__ == "__main__":
    unittest.main()

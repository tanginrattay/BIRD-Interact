"""Verify restored simulator protocol matches the original Git baseline."""
import ast
import subprocess
import unittest
from pathlib import Path

from user_simulator import server


class ReferenceProtocolTests(unittest.TestCase):
    def test_original_protocol_functions_are_identical(self):
        root = Path(__file__).resolve().parent.parent
        baseline = subprocess.check_output(
            ['git', 'show', '451fe2c:BIRD-Interact-ADK/user_simulator/server.py'], text=True)
        def definitions(source):
            return {n.name: ast.dump(n, include_attributes=False)
                    for n in ast.parse(source).body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        original = definitions(baseline)
        current = definitions((root / 'user_simulator/server.py').read_text())
        for name, definition in original.items():
            if name != '_call_llm':
                with self.subTest(name=name):
                    self.assertEqual(current[name], definition)

    def test_original_prompts_and_request_tools_are_identical(self):
        root = Path(__file__).resolve().parent.parent
        for name in ('user_simulator/prompts.py', 'shared/models.py', 'system_agent/tools.py',
                     'system_agent/agent.py', 'system_agent/callbacks.py'):
            with self.subTest(name=name):
                original = subprocess.check_output(
                    ['git', 'show', f'451fe2c:BIRD-Interact-ADK/{name}'])
                self.assertEqual((root / name).read_bytes(), original)


if __name__ == '__main__':
    unittest.main()

import unittest
from nodes import code_execution_runtime_node

# Handcrafted malicious attack payloads to dry-run compile
MALICIOUS_PAYLOADS = [
    {
        "name": "requests import",
        "code": "def compute_metrics():\n    import requests\n    return requests.get('https://google.com').status_code"
    },
    {
        "name": "socket raw connection",
        "code": "def compute_metrics():\n    import socket\n    s = socket.socket()\n    s.connect(('google.com', 80))\n    return 'connected'"
    },
    {
        "name": "urllib standard library",
        "code": "def compute_metrics():\n    import urllib.request\n    return urllib.request.urlopen('https://google.com').read()"
    }
]

class TestSecurityGate(unittest.TestCase):
    
    def test_malicious_imports_are_blocked(self):
        """
        Directly feeds malicious nested imports into our sandbox execution compiler
        to guarantee they are intercepted and failed before hitting execution scope.
        """
        for case in MALICIOUS_PAYLOADS:
            name = case["name"]
            code = case["code"]
            
            initial_state = {"generated_code": code, "execution_error": ""}
            
            # Run through compile runtime
            output_state = code_execution_runtime_node(initial_state)
            
            # Assertions to ensure state returns with execution errors and is caught
            self.assertIsNotNone(
                output_state.get("execution_error"), 
                f"Security Breach! {name} leaked past compilation gate."
            )
            self.assertIn(
                "not available in this environment", 
                output_state.get("execution_error").lower(),
                f"Unexpected error message for {name}: {output_state.get('execution_error')}"
            )

if __name__ == "__main__":
    unittest.main()
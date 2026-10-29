"""Regression: Gemini thought-signatures must survive tool-calling sessions.

The current OpenAI-compatible editor does not guarantee that preservation.
These offline tests verify that direct Gemini is never selected for tool turns.
"""
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from router.app import KEY, accepts_request, app, requires_tools
from router.config import Provider
from router.store import Store
from pathlib import Path
from tempfile import TemporaryDirectory


def fake_provider(name):
    ids = {"gemini": "gemini-3.8-flash", "kilo": "kilo-auto/free",
           "openrouter": "openrouter/free"}
    return Provider(name=name, model=ids[name],
                    url="https://" + name + ".example/v1/chat/completions",
                    key="dummy", context=60000)


class GeminiToolSignatureProtection(unittest.TestCase):
    def test_declared_tools_require_a_compatible_route(self):
        payload = {"messages": [{"role": "user", "content": "Add image upload"}],
                   "tools": [{"type": "function", "function": {
                       "name": "shell", "parameters": {"type": "object"}}}]}
        self.assertTrue(requires_tools(payload))
        self.assertFalse(accepts_request(fake_provider("gemini"), payload))
        self.assertTrue(accepts_request(fake_provider("kilo"), payload))
        self.assertTrue(accepts_request(fake_provider("openrouter"), payload))

    def test_historic_tool_call_is_enough_even_if_tools_omitted(self):
        payload = {"messages": [
            {"role": "user", "content": "Add upload API"},
            {"role": "assistant", "tool_calls": [{
                "id": "call_1", "type": "function",
                "function": {"name": "shell", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "call_1", "content": "done"},
        ]}
        self.assertTrue(requires_tools(payload))
        self.assertFalse(accepts_request(fake_provider("gemini"), payload))

    def test_text_only_still_allows_gemini(self):
        payload = {"messages": [{"role": "user", "content": "Explain multipart"}]}
        self.assertFalse(requires_tools(payload))
        self.assertTrue(accepts_request(fake_provider("gemini"), payload))

    def test_gemini_only_returns_descriptive_503_not_signature_400(self):
        with TemporaryDirectory() as folder, Store(str(Path(folder)/"calls.db")) as store:
            with patch("router.app.FREE_PROVIDERS", [fake_provider("gemini")]), \
                 patch("router.app.DB", store):
                with TestClient(app) as client:
                    response = client.post(
                        "/v1/chat/completions",
                        headers={"Authorization": "Bearer " + KEY},
                        json={"model": "auto-coder",
                              "messages": [{"role": "user", "content": "Edit a file"}],
                              "tools": [{"type": "function", "function": {
                                  "name": "shell", "parameters": {}}}]})
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.json()["error"]["code"],
                                     "FREE_TOOL_CAPACITY_UNAVAILABLE")
                    status = client.get("/router/status", headers={
                        "Authorization": "Bearer " + KEY}).json()
                    self.assertTrue(status["any_available"])
                    self.assertFalse(status["any_tool_available"])
                    self.assertFalse(status["providers"][0]["tool_eligible"])

    def test_tool_request_uses_kilo_not_gemini_even_if_first_in_order(self):
        hosts = []
        def respond(request):
            hosts.append(request.url.host)
            return httpx.Response(200, json={
                "id": "demo", "object": "chat.completion",
                "choices": [{"index": 0, "message": {
                    "role": "assistant", "content": "Ready"},
                    "finish_reason": "stop"}]})
        with TemporaryDirectory() as folder, Store(str(Path(folder)/"calls.db")) as store:
            with patch("router.app.FREE_PROVIDERS",
                       [fake_provider("gemini"), fake_provider("kilo")]), \
                 patch("router.app.DB", store):
                with TestClient(app) as client:
                    transport = httpx.AsyncClient(transport=httpx.MockTransport(respond))
                    app.state.client = transport
                    reply = client.post(
                        "/v1/chat/completions",
                        headers={"Authorization": "Bearer " + KEY},
                        json={"model": "auto-coder",
                              "messages": [{"role": "user", "content": "Build image uploader"}],
                              "tools": [{"type": "function", "function": {
                                  "name": "shell", "parameters": {}}}]})
                    self.assertEqual(reply.status_code, 200, reply.text)
                    self.assertEqual(hosts, ["kilo.example"])


if __name__ == "__main__":
    unittest.main()

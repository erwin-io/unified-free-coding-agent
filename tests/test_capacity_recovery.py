"""Capacity and provider failover must not reject a half-used context."""
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient

from router.app import app, KEY, candidates, status_for
from router.config import Provider
from router.store import Store

def fake(name, context=1000):
    return Provider(name, "https://"+name+".example/v1/chat/completions",
                    ("kilo-auto/free" if name=="kilo" else "openrouter/free"),
                    "fake-key", context=context)

class ProviderRecovery(unittest.TestCase):
    def test_bad_json_token_estimate_does_not_block_routing(self):
        with TemporaryDirectory() as td, Store(str(Path(td)/"use.sqlite")) as db:
            with patch("router.app.DB", db), patch("router.app.FREE_PROVIDERS", [fake("kilo")]):
                body={"messages":[{"role":"user", "content":"a"*10000}],
                      "tools":[{"type":"function","function":{"name":"shell","parameters":{}}}]}
                self.assertEqual([p.name for p in candidates(body)],["kilo"])

    def test_429_switches_to_second_provider_without_new_user_prompt(self):
        calls=[]
        def route(request):
            calls.append(request.url.host)
            if request.url.host=="kilo.example":
                return httpx.Response(429, headers={"Retry-After":"180"},
                                      json={"error":{"message":"rate limited"}})
            return httpx.Response(200, json={"id":"ok","object":"chat.completion",
                "choices":[{"index":0,"message":{"role":"assistant","content":"Done"},
                            "finish_reason":"stop"}]})
        with TemporaryDirectory() as td, Store(str(Path(td)/"use.sqlite")) as db:
            with patch("router.app.DB",db), patch("router.app.FREE_PROVIDERS",
                [fake("kilo"), fake("openrouter")]):
                with TestClient(app) as client:
                    client.app.state.client=httpx.AsyncClient(transport=httpx.MockTransport(route))
                    answer=client.post("/v1/chat/completions",
                        headers={"Authorization":"Bearer "+KEY},
                        json={"model":"auto-coder","messages":[{"role":"user","content":"write code"}],
                              "tools":[{"type":"function","function":{"name":"shell","parameters":{}}}]})
                    self.assertEqual(answer.status_code,200,answer.text)
                    self.assertEqual(answer.headers["X-Local-Router-Provider"],"openrouter")
                    self.assertEqual(calls,["kilo.example","openrouter.example"])
                    self.assertGreaterEqual(db.cooldown("kilo")[0],170)

    def test_no_provider_reports_cooldown_reason_and_retry_after(self):
        with TemporaryDirectory() as td, Store(str(Path(td)/"use.sqlite")) as db:
            db.block("kilo",120,"HTTP_429")
            with patch("router.app.DB",db), patch("router.app.FREE_PROVIDERS",[fake("kilo")]):
                with TestClient(app) as client:
                    res=client.post("/v1/chat/completions",
                        headers={"Authorization":"Bearer "+KEY},
                        json={"model":"auto-coder","messages":[{"role":"user","content":"build"}],
                              "tools":[{"type":"function","function":{"name":"shell","parameters":{}}}]})
                    self.assertEqual(res.status_code,503)
                    self.assertEqual(res.json()["error"]["providers"][0]["reason"],"HTTP_429")
                    self.assertGreater(int(res.headers["Retry-After"]),0)

    def test_local_cap_wait_reports_why(self):
        with TemporaryDirectory() as td, Store(str(Path(td)/"use.sqlite")) as db:
            p=Provider("kilo","https://kilo.example/v1","kilo-auto/free","",hour_cap=1)
            db.add("kilo",200,2)
            with patch("router.app.DB",db):
                s=status_for(p)
                self.assertFalse(s["eligible"])
                self.assertIn("LOCAL_REQUEST_CAP",s["reason"])
                self.assertGreater(s["eligible_in_seconds"],0)

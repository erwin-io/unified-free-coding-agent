import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch
from router.app import app


class RouterApi(unittest.TestCase):
    def test_health_is_local_and_free_only(self):
        with TestClient(app) as client:
            reply=client.get("/health")
            self.assertEqual(reply.status_code,200)
            self.assertEqual(reply.json()["mode"],"FREE_ONLY")

    def test_requires_local_auth(self):
        with TestClient(app) as client:
            self.assertEqual(client.get("/v1/models").status_code,401)
            self.assertEqual(client.get("/router/status").status_code,401)

    def test_alias_disallows_paid_model(self):
        from router.app import KEY
        with TestClient(app) as client:
            reply=client.post("/v1/chat/completions",
                headers={"Authorization":"Bearer "+KEY},
                json={"model":"any-paid-model",
                      "messages":[{"role":"user","content":"hello"}]})
            self.assertEqual(reply.status_code,400)

    def test_no_capacity_explicit_503(self):
        from router.app import KEY
        with patch("router.app.FREE_PROVIDERS",[]):
            with TestClient(app) as client:
                reply=client.post("/v1/chat/completions",
                    headers={"Authorization":"Bearer "+KEY},
                    json={"model":"auto-coder",
                          "messages":[{"role":"user","content":"hello"}]})
                self.assertEqual(reply.status_code,503)
                self.assertEqual(reply.json()["error"]["code"],"FREE_CAPACITY_EXHAUSTED")


if __name__=="__main__":
    unittest.main()

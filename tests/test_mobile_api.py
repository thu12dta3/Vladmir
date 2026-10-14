import json
import http.client
import os
import stat
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mark.config import load_config
from mark.mobile_api import MobileServer, mobile_token
from mark.model_state import ModelSession
from mark.memory import SharedMemory, ShortMemory
from mark.agenda import Agenda
from mark.missions import MissionStore
from mark.core.context import CoreContext


class FakeSession:
    def __init__(self, model_key=None):
        self.awake = False
        self.model_key = model_key

    def wake(self):
        self.awake = True

    def sleep(self):
        self.awake = False


class MobileAPITests(unittest.TestCase):
    def setUp(self):
        self.agenda_directory = TemporaryDirectory()
        agenda_path = Path(self.agenda_directory.name) / "agenda.sqlite3"
        mission_path = Path(self.agenda_directory.name) / "missions.sqlite3"
        with patch("mark.mobile_api.Agenda", side_effect=lambda: Agenda(agenda_path)):
            self.server = MobileServer(load_config(), "test-private-token", 0, memory=ShortMemory(),
                                        mission_store=MissionStore(mission_path))
        self.server.model_sessions = {"chat": FakeSession("chat"), "call": FakeSession("call"),
                                      "engineer": FakeSession("engineer")}
        self.server.model_session = self.server.model_sessions["call"]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.agenda_directory.cleanup()

    def request(self, path, payload=None, token="test-private-token"):
        headers = {"Authorization": "Bearer " + token}
        body = None if payload is None else json.dumps(payload).encode()
        if body is not None:
            headers["Content-Type"] = "application/json"
        return urllib.request.Request(self.base + path, data=body, headers=headers)

    def test_models_requires_token_and_exposes_both_profiles(self):
        with self.assertRaises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(self.request("/v1/models", token="wrong"), timeout=3)
        self.assertEqual(denied.exception.code, 401)
        denied.exception.close()
        with urllib.request.urlopen(self.request("/v1/models"), timeout=3) as response:
            catalog = json.load(response)
        self.assertEqual([item["id"] for item in catalog["data"]], ["vladmir", "vladmir-call"])

    def test_agenda_endpoint_requires_token_and_returns_shared_items(self):
        with self.assertRaises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(self.request("/v1/agenda", token="wrong"), timeout=3)
        self.assertEqual(denied.exception.code, 401)
        denied.exception.close()
        with urllib.request.urlopen(self.request("/v1/agenda"), timeout=3) as response:
            self.assertEqual(json.load(response), {"items": []})

    def test_history_endpoint_requires_token_and_returns_shared_conversation(self):
        self.server.memory.add("pergunta no PC", "resposta no PC")
        with self.assertRaises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(self.request("/v1/history", token="wrong"), timeout=3)
        self.assertEqual(denied.exception.code, 401)
        denied.exception.close()
        with urllib.request.urlopen(self.request("/v1/history"), timeout=3) as response:
            history = json.load(response)
        self.assertEqual(history["items"][0]["user"], "pergunta no PC")
        self.assertEqual(history["items"][0]["assistant"], "resposta no PC")

    def test_call_page_and_root_close_idle_http_connections(self):
        from urllib.parse import urlsplit
        target = urlsplit(self.base)
        conn = http.client.HTTPConnection(target.hostname, target.port, timeout=3)
        try:
            conn.request("GET", "/")
            redirected = conn.getresponse()
            self.assertEqual(redirected.status, 302)
            self.assertEqual(redirected.getheader("Connection"), "close")
        finally:
            conn.close()
        conn = http.client.HTTPConnection(target.hostname, target.port, timeout=3)
        try:
            conn.request("GET", "/call")
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader("Connection"), "close")
        finally:
            conn.close()

    def test_chat_uses_mark_brain_and_conversation_history(self):
        payload = {"model": "vladmir", "messages": [
            {"role": "system", "content": "Persona do app"},
            {"role": "user", "content": "oi"},
            {"role": "assistant", "content": "olá"},
            {"role": "user", "content": "que horas são?"},
        ]}
        with patch("mark.mobile_api.answer", return_value="Agora são 10h00.") as brain:
            with urllib.request.urlopen(self.request("/v1/chat/completions", payload), timeout=3) as response:
                result = json.load(response)
        self.assertEqual(brain.call_args.args[0], "que horas são?")
        self.assertIn("Usuário: oi\nVladmir: olá", brain.call_args.args[2].render())
        self.assertEqual(brain.call_args.args[1]["ollama"]["model"], load_config()["models"]["call"])
        self.assertEqual(result["choices"][0]["message"]["content"], "Agora são 10h00.")

    def test_general_can_create_inert_engineer_mission_from_chat(self):
        payload = {"model": "vladmir", "messages": [{"role": "user", "content":
            "Vladmir, peça ao Engineer para revisar o projeto Python desta pasta."}]}
        request = self.request("/v1/chat/completions", payload)
        request.add_header("X-Vladmir-Client", "desktop")
        with patch("mark.mobile_api.answer") as brain:
            with urllib.request.urlopen(request, timeout=3) as response:
                content = json.load(response)["choices"][0]["message"]["content"]
        self.assertIn("Nenhum arquivo foi lido ou alterado", content)
        self.assertIn("autorização local", content)
        brain.assert_not_called()
        missions = self.server.mission_store.list_missions()
        self.assertEqual(len(missions), 1)
        self.assertEqual(missions[0]["state"], "WAITING_APPROVAL")
        self.assertIsNone(missions[0]["workspace"])

    def test_general_reports_actual_mission_status_without_calling_model(self):
        mission_id = self.server.mission_store.create_conversation_draft("Revisar o projeto Python")
        payload = {"model": "vladmir", "messages": [{"role": "user", "content":
            "Como está a revisão que pedi ao Engineer?"}]}
        request = self.request("/v1/chat/completions", payload)
        request.add_header("X-Vladmir-Client", "desktop")
        with patch("mark.mobile_api.answer") as brain:
            with urllib.request.urlopen(request, timeout=3) as response:
                content = json.load(response)["choices"][0]["message"]["content"]
        self.assertIn(mission_id[:8], content)
        self.assertIn("aguardando autorização local", content)
        brain.assert_not_called()

    def test_call_uses_general_mission_status_reply_from_persisted_state(self):
        mission_id = self.server.mission_store.create_conversation_draft("Revisar o projeto Python")
        self.server.cfg["paths"]["tmp"] = self.agenda_directory.name
        request = urllib.request.Request(
            self.base + "/v1/voice/turn", data=b"\0" * 6000, method="POST",
            headers={"Authorization": "Bearer test-private-token", "Content-Type": "application/octet-stream"},
        )
        with patch("mark.mobile_api.transcribe_temporary", return_value="Como está a revisão que pedi?"), \
             patch("mark.mobile_api.speech_wav", return_value=b"RIFF-test") as speak, \
             patch("mark.mobile_api.answer") as brain:
            with urllib.request.urlopen(request, timeout=3) as response:
                self.assertEqual(response.headers.get_content_type(), "audio/wav")
        self.assertIn(mission_id[:8], speak.call_args.args[0])
        self.assertIn("aguardando autorização local", speak.call_args.args[0])
        brain.assert_not_called()

    def test_voice_profile_uses_fast_model_and_shared_answer_path(self):
        handler = self._handler()
        with patch("mark.mobile_api.answer", return_value="Resposta rápida") as brain:
            reply = handler._answer("alô", self.server.memory, "call")
        self.assertEqual(reply, "Resposta rápida")
        self.assertEqual(brain.call_args.args[1]["ollama"]["model"], load_config()["models"]["call"])

    def test_localmind_mark_call_alias_selects_fast_profile(self):
        payload = {"model": "vladmir-call", "messages": [{"role": "user", "content": "olá"}]}
        with patch("mark.mobile_api.answer", return_value="Olá.") as brain:
            with urllib.request.urlopen(self.request("/v1/chat/completions", payload), timeout=3):
                pass
        self.assertEqual(brain.call_args.args[1]["ollama"]["model"], load_config()["models"]["call"])

    def test_desktop_request_is_tagged_separately_from_legacy_client(self):
        payload = {"model": "vladmir", "messages": [{"role": "user", "content": "oi"}]}
        request = self.request("/v1/chat/completions", payload)
        request.add_header("X-Vladmir-Client", "desktop")
        with patch("mark.mobile_api.answer", return_value="Olá") as brain:
            with urllib.request.urlopen(request, timeout=3):
                pass
        self.assertEqual(brain.call_args.kwargs["origin"], "pc")
        self.assertEqual(self.server.memory.items[-1]["source"], "desktop-chat")

    def test_client_context_reaches_shared_answer_pipeline(self):
        payload = {
            "model": "vladmir",
            "vladmir_context": {"specialization": "engineer", "session_id": "mobile-session",
                             "project_id": "mark-core", "task_id": "api-test"},
            "messages": [{"role": "user", "content": "revise a API"}],
        }
        with patch("mark.mobile_api.answer", return_value="Revisado.") as brain:
            with urllib.request.urlopen(self.request("/v1/chat/completions", payload), timeout=3):
                pass
        context = brain.call_args.kwargs["context"]
        self.assertEqual(context.specialization, "engineer")
        self.assertEqual(context.session_id, "mobile-session")
        self.assertEqual(context.project_id, "mark-core")
        self.assertEqual(context.task_id, "api-test")
        self.assertEqual(context.source, "api-chat")

    def test_unknown_specialization_is_rejected_without_answering(self):
        payload = {"model": "vladmir", "vladmir_context": {"specialization": "root"},
                   "messages": [{"role": "user", "content": "oi"}]}
        with patch("mark.mobile_api.answer") as brain:
            with self.assertRaises(urllib.error.HTTPError) as response:
                urllib.request.urlopen(self.request("/v1/chat/completions", payload), timeout=3)
        self.assertEqual(response.exception.code, 400)
        response.exception.close()
        brain.assert_not_called()

    def test_engineer_specialization_selects_configured_coder_profile(self):
        handler = self._handler()
        self.server.model_sessions["chat"].wake()
        context = CoreContext.create(specialization="engineer")
        with patch("mark.mobile_api.direct_response", return_value=None), \
             patch("mark.mobile_api.try_public_answer", return_value=None), \
             patch("mark.mobile_api.answer", return_value="Código revisado.") as brain:
            result = handler._answer("revise este código Python", self.server.memory,
                                     "chat", context=context)
        self.assertEqual(result, "Código revisado.")
        self.assertEqual(brain.call_args.args[1]["ollama"]["model"],
                         "qwen2.5-coder:7b")
        self.assertTrue(self.server.model_sessions["engineer"].awake)
        self.assertFalse(self.server.model_sessions["chat"].awake)

    def test_engineer_image_stays_on_multimodal_general_model(self):
        handler = self._handler()
        context = CoreContext.create(specialization="engineer")
        with patch("mark.mobile_api.direct_response", return_value=None), \
             patch("mark.mobile_api.try_public_answer", return_value=None), \
             patch("mark.mobile_api.answer", return_value="Imagem analisada.") as brain:
            handler._answer("explique este screenshot", self.server.memory, "chat",
                            images=["aW1hZ2U="], context=context)
        self.assertEqual(brain.call_args.args[1]["ollama"]["model"],
                         load_config()["models"]["chat"])

    def test_missing_engineer_model_falls_back_to_general_without_download(self):
        class MissingSession(FakeSession):
            def wake(self):
                raise RuntimeError("model missing")
        handler = self._handler()
        self.server.model_sessions["engineer"] = MissingSession()
        context = CoreContext.create(specialization="engineer")
        with patch("mark.mobile_api.direct_response", return_value=None), \
             patch("mark.mobile_api.try_public_answer", return_value=None), \
             patch("mark.mobile_api.answer", return_value="Resposta Geral.") as brain:
            result = handler._answer("revise este código Python", self.server.memory,
                                     "chat", context=context)
        self.assertTrue(result.startswith("O modelo especializado do Engineer não está disponível"))
        self.assertEqual(brain.call_args.args[1]["ollama"]["model"],
                         load_config()["models"]["chat"])
        self.assertTrue(self.server.model_sessions["chat"].awake)

    def test_engineer_inference_error_uses_one_general_fallback(self):
        from mark.brain_model import EngineerModelError
        handler = self._handler()
        context = CoreContext.create(specialization="engineer")
        with patch("mark.mobile_api.direct_response", return_value=None), \
             patch("mark.mobile_api.try_public_answer", return_value=None), \
             patch("mark.mobile_api.answer", side_effect=[EngineerModelError(), "Resposta Geral."]) as brain:
            result = handler._answer("depure este código", self.server.memory,
                                     "chat", context=context)
        self.assertIn("falhou; respondi usando o modelo Geral", result)
        self.assertEqual(brain.call_count, 2)
        self.assertEqual(brain.call_args_list[0].args[1]["ollama"]["model"],
                         "qwen2.5-coder:7b")
        self.assertEqual(brain.call_args_list[1].args[1]["ollama"]["model"],
                         load_config()["models"]["chat"])

    def test_signed_device_is_identified_as_phone(self):
        handler = self._handler()
        handler._device_id = "test-device"
        self.assertEqual(handler._origin(), "celular")
        self.assertEqual(handler._source("call"), "mobile-call")

    def test_agenda_command_does_not_wake_either_model(self):
        handler = self._handler()
        with patch("mark.mobile_api.answer", side_effect=AssertionError("agenda local")):
            reply = handler._answer("o que tenho hoje?", self.server.memory, "chat")
        self.assertIn("agenda está vazia", reply)
        self.assertFalse(self.server.model_sessions["chat"].awake)
        self.assertFalse(self.server.model_sessions["call"].awake)

    def test_general_globe_request_uses_mcp_in_shared_answer_path(self):
        handler = self._handler()
        manager = Mock()
        manager.running = True
        manager.call_tool.return_value = {"structuredContent": {"url": "http://127.0.0.1:4173/#v=2"}}
        with patch.object(self.server, "_godseye", return_value=manager), \
             patch("mark.gods_eye_intent.webbrowser.open", return_value=True) as open_browser, \
             patch("mark.mobile_api.answer", side_effect=AssertionError("o comando não deve ir ao Qwen")):
            reply = handler._answer("Mostre Curitiba no globo", self.server.memory, "chat")
        self.assertIn("Curitiba", reply)
        manager.start.assert_called_once_with()
        self.assertEqual(manager.call_tool.call_args.args[0], "show_in_gods_eye_view")
        open_browser.assert_called_once()

    def test_call_profile_uses_same_explicit_globe_route(self):
        handler = self._handler()
        manager = Mock()
        manager.running = True
        manager.call_tool.return_value = {"structuredContent": {"url": "http://127.0.0.1:4173/#v=2"}}
        with patch.object(self.server, "_godseye", return_value=manager), \
             patch("mark.gods_eye_intent.webbrowser.open", return_value=True), \
             patch("mark.mobile_api.answer", side_effect=AssertionError("o comando não deve ir ao Qwen")):
            reply = handler._answer("Abra o globo", self.server.memory, "call")
        self.assertIn("God's Eye View", reply)
        manager.call_tool.assert_called_once()

    def _handler(self):
        from mark.mobile_api import MobileHandler
        handler = object.__new__(MobileHandler)
        handler.server = self.server
        return handler

    def test_streaming_uses_openai_sse_format(self):
        payload = {"model": "vladmir", "stream": True,
                   "messages": [{"role": "user", "content": "diga olá"}]}
        with patch("mark.mobile_api.answer", return_value="Olá."):
            with urllib.request.urlopen(self.request("/v1/chat/completions", payload), timeout=3) as response:
                stream = response.read().decode()
        self.assertIn('"object": "chat.completion.chunk"', stream)
        self.assertIn('"content": "Olá."', stream)
        self.assertTrue(stream.endswith("data: [DONE]\n\n"))

    def test_mobile_goodbye_returns_to_sleep_without_calling_brain(self):
        payload = {"model": "vladmir", "messages": [{"role": "user", "content": "pode descansar"}]}
        self.server.model_session.wake()
        with patch("mark.mobile_api.answer", side_effect=AssertionError("Qwen desnecessário")):
            with urllib.request.urlopen(self.request("/v1/chat/completions", payload), timeout=3) as response:
                result = json.load(response)
        self.assertFalse(self.server.model_session.awake)
        self.assertIn("descansar", result["choices"][0]["message"]["content"])

    def test_mobile_token_is_private_and_stable(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "mobile.token"
            first = mobile_token(path)
            self.assertEqual(mobile_token(path), first)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertGreaterEqual(len(first), 40)


class ModelSessionTests(unittest.TestCase):
    def test_qwen_stays_loaded_until_last_active_session_sleeps(self):
        with TemporaryDirectory() as directory, patch("mark.model_state._model_command") as command:
            first_cfg = load_config()
            second_cfg = load_config()
            first = ModelSession(first_cfg, Path(directory))
            second = ModelSession(second_cfg, Path(directory))
            first.wake()
            second.wake()
            self.assertEqual(first_cfg["ollama"]["keep_alive"], -1)
            first.sleep()
            self.assertTrue(second.awake)
            self.assertEqual([args.args[1] for args in command.call_args_list], [-1, -1])
            second.sleep()
            self.assertEqual([args.args[1] for args in command.call_args_list], [-1, -1, 0])
            self.assertEqual(second_cfg["ollama"]["keep_alive"], 0)

    def test_sessions_keep_chat_and_call_models_independently(self):
        with TemporaryDirectory() as directory, patch("mark.model_state._model_command") as command:
            chat_cfg = load_config()
            chat_cfg["ollama"]["model"] = "qwen3-vl:4b-instruct"
            call_cfg = load_config()
            call_cfg["ollama"]["model"] = "qwen3-vl:4b-instruct"
            chat = ModelSession(chat_cfg, Path(directory))
            call = ModelSession(call_cfg, Path(directory))
            chat.wake()
            call.wake()
            chat.sleep()
            self.assertFalse(chat.awake)
            self.assertTrue(call.awake)
            self.assertEqual(command.call_args_list[-1].args[0]["ollama"]["model"], "qwen3-vl:4b-instruct")
            call.sleep()

    def test_explicit_sleep_cleans_a_stale_session_after_restart(self):
        with TemporaryDirectory() as directory, patch("mark.model_state._model_command") as command:
            state = Path(directory)
            stale = state / "session-99999999-obsolete"
            stale.touch(mode=0o600)
            session = ModelSession(load_config(), state)
            session.sleep()
            self.assertFalse(stale.exists())
            self.assertEqual(command.call_count, 1)
            self.assertEqual(command.call_args.args[1], 0)


class SharedMemoryTests(unittest.TestCase):
    def test_same_conversation_is_visible_to_two_process_instances(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state" / "conversation.sqlite3"
            phone = SharedMemory(6, path)
            helmet = SharedMemory(6, path)
            phone.add("meu nome é Alex", "Prazer, Alex.", source="mobile-chat")
            self.assertIn("meu nome é Alex", helmet.render())
            helmet.add("qual é meu nome?", "Alex.", source="pc-voice")
            self.assertIn("qual é meu nome?", phone.render())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            helmet.clear()
            self.assertEqual(phone.render(), "Nenhuma.")


if __name__ == "__main__":
    unittest.main()

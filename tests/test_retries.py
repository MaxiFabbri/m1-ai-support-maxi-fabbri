import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backoff import call_with_backoff, CuotaAgotadaError, ReintentosAgotadosError, leer_retry_after
from providers.base import Provider
from router import Router


class RateLimitError(Exception):
    status_code = 429
    retry_after = 0


class RetryTests(unittest.TestCase):
    def consultar(self, provider):
        messages = [{"role": "user", "content": "Consulta"}]
        parameters = {"temperature": 0.2, "top_p": 0.85, "max_output_tokens": 50}

        def consulta():
            return provider.ask(messages, parameters)

        return call_with_backoff(consulta)

    def test_router_does_not_retry_or_wait(self):
        provider = Mock(spec=Provider)
        error = RateLimitError()
        provider.ask.side_effect = error
        config = Mock(default_provider="gemini")
        with patch("router.GeminiProvider", return_value=provider):
            router = Router(config)
        with patch("backoff.time.sleep") as sleep:
            with self.assertRaises(RateLimitError) as raised:
                router.ask([], {})
        self.assertIs(raised.exception, error)
        provider.ask.assert_called_once_with([], {})
        sleep.assert_not_called()

    def test_retry_reuses_prepared_messages_and_parameters(self):
        provider = Mock(spec=Provider)
        provider.ask.side_effect = [RateLimitError(), "ok"]
        with patch("backoff.time.sleep") as sleep, redirect_stderr(io.StringIO()):
            result = self.consultar(provider)
        self.assertEqual(result, "ok")
        sleep.assert_called_once_with(0.0)
        first = provider.ask.call_args_list[0].args
        second = provider.ask.call_args_list[1].args
        self.assertIs(first[0], second[0])
        self.assertIs(first[1], second[1])

    def test_exhaustion_keeps_five_total_calls_and_four_waits(self):
        provider = Mock(spec=Provider)
        provider.ask.side_effect = RateLimitError()
        with patch("backoff.time.sleep") as sleep, redirect_stderr(io.StringIO()):
            with self.assertRaises(ReintentosAgotadosError):
                self.consultar(provider)
        self.assertEqual(provider.ask.call_count, 5)
        self.assertEqual(sleep.call_count, 4)

    def test_quota_exhaustion_is_not_retried(self):
        provider = Mock(spec=Provider)
        error = RateLimitError()
        error.code = "insufficient_quota"
        provider.ask.side_effect = error
        with patch("backoff.time.sleep") as sleep:
            with self.assertRaises(CuotaAgotadaError):
                self.consultar(provider)
        provider.ask.assert_called_once()
        sleep.assert_not_called()

    def test_non_429_errors_are_not_retried(self):
        provider = Mock(spec=Provider)
        error = RuntimeError("Unauthorized")
        error.status_code = 401
        provider.ask.side_effect = error
        with patch("backoff.time.sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "Unauthorized"):
                self.consultar(provider)
        provider.ask.assert_called_once()
        sleep.assert_not_called()

    def test_retry_after_and_gemini_delay_are_preserved(self):
        error = Exception()
        error.response = Mock(headers={"retry-after": "2.5"})
        self.assertEqual(leer_retry_after(error), 2.5)
        error.response = Mock(headers={})
        error.details = {"error": {"details": [{
            "@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "3s"
        }]}}
        self.assertEqual(leer_retry_after(error), 3)


if __name__ == "__main__":
    unittest.main()

import unittest

from tests import _env  # noqa: F401
from dvdy.errors import ACTION_LABELS, friendly, is_cookie_error


class FriendlyTest(unittest.TestCase):
    def check(self, raw, action, contains):
        msg, act = friendly(raw)
        self.assertEqual(act, action, raw)
        self.assertIn(contains, msg)

    def test_reglas(self):
        self.check("ERROR: [youtube] abc: Private video. Sign in if you've been granted access", "browser", "privado")
        self.check("Sign in to confirm your age. This video may be inappropriate for some users.", "browser", "edad")
        self.check("Sign in to confirm you're not a bot", "retry", "robot")
        self.check("Unsupported URL: https://example.com", None, "no es compatible")
        self.check("ffprobe and ffmpeg not found. Please install", "ffmpeg", "FFmpeg")
        self.check("HTTP Error 403: Forbidden", "update", "yt-dlp")
        self.check("<urlopen error [Errno 11001] getaddrinfo failed>", "retry", "conexión")
        self.check("HTTP Error 429: Too Many Requests", "retry", "demasiados")
        self.check("[Errno 28] No space left on device", None, "espacio")

    def test_cookies(self):
        raw = "Could not copy Chrome cookie database. See https://github.com/yt-dlp/yt-dlp/issues/7271"
        self.assertEqual(friendly(raw)[1], "nocookies")
        self.assertTrue(is_cookie_error(raw))
        self.assertFalse(is_cookie_error("HTTP Error 403: Forbidden"))

    def test_desconocido_y_vacio(self):
        self.assertEqual(friendly("algo rarísimo")[1], "retry")
        self.assertEqual(friendly(None)[1], "retry")

    def test_todas_las_acciones_tienen_texto(self):
        from dvdy.errors import _RULES
        for _, _, action in _RULES:
            if action:
                self.assertIn(action, ACTION_LABELS)


if __name__ == "__main__":
    unittest.main()

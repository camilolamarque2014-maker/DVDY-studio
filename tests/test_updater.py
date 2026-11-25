import unittest

from tests import _env  # noqa: F401
from dvdy.config import APP_VERSION
from dvdy.updater import brief_notes, parse_version


class UpdaterTest(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version("v2.3.2"), (2, 3, 2))
        self.assertEqual(parse_version("2.4"), (2, 4, 0))
        self.assertIsNone(parse_version("latest"))
        self.assertIsNone(parse_version(None))
        self.assertGreater(parse_version("v2.10.0"), parse_version("v2.9.9"))

    def test_version_de_la_app_es_valida(self):
        self.assertIsNotNone(parse_version(APP_VERSION))

    def test_brief_notes_corta_en_instalacion(self):
        md = "## Correcciones\n- Arreglo\n\n## Instalación\n1. Descarga"
        out = brief_notes(md)
        self.assertIn("**Correcciones**", out)
        self.assertNotIn("Descarga", out)

    def test_brief_notes_largas(self):
        out = brief_notes("línea\n" * 500, max_chars=100)
        self.assertLessEqual(len(out), 110)
        self.assertTrue(out.endswith("…"))


if __name__ == "__main__":
    unittest.main()

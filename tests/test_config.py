import json
import os
import unittest

from tests import _env
from dvdy import config


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(config.HISTORY_FILE.startswith(_env.TMP), "las pruebas no deben tocar el historial real")
        if os.path.exists(config.HISTORY_FILE):
            os.remove(config.HISTORY_FILE)

    def test_guardar_y_recargar(self):
        h = config.History()
        h.add("Canción", "Música", r"C:\Music\cancion.mp3", "https://example.com/v")
        h.add("Video", "Video", "")
        again = config.History()
        self.assertEqual([i["title"] for i in again.items], ["Video", "Canción"])
        self.assertFalse(os.path.exists(config.HISTORY_FILE + ".tmp"), "no debe quedar el temporal")

    def test_escritura_fallida_no_borra_el_anterior(self):
        h = config.History()
        h.add("Original", "Video", "")
        h.items.insert(0, {"title": object()})  # no se puede convertir a JSON
        with self.assertRaises(TypeError):
            h._save()
        with open(config.HISTORY_FILE, encoding="utf-8") as f:
            self.assertEqual(json.load(f)[0]["title"], "Original")

    def test_limite(self):
        h = config.History()
        h.items = [{"title": str(i)} for i in range(config.History.MAX + 5)]
        h.add("nuevo", "Video", "")
        self.assertEqual(len(h.items), config.History.MAX)


class ConfigTest(unittest.TestCase):
    def test_valores_por_defecto(self):
        c = config.Config()
        self.assertEqual(c["max_concurrent"], 2)
        self.assertEqual(c["theme"], "auto")
        self.assertIsNone(c.get("no_existe"))


if __name__ == "__main__":
    unittest.main()

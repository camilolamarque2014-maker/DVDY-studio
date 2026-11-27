"""Herramientas de FFmpeg: una imagen tiene que salir como imagen, no como video H.264."""
import unittest

from tests import _env

try:
    from dvdy import page_tools
    HAS_QT = True
except ImportError:  # page_tools importa PySide6
    HAS_QT = False

from dvdy.utils import image_output_args, is_image_file


class ImageArgsTest(unittest.TestCase):
    def test_es_imagen(self):
        self.assertTrue(is_image_file("/x/foto.JPG"))
        self.assertTrue(is_image_file("a.webp"))
        self.assertFalse(is_image_file("anim.gif"), "el GIF puede ser animado: se trata como video")
        self.assertFalse(is_image_file("video.mp4"))

    def test_codificador_segun_extension(self):
        self.assertIn("mjpeg", image_output_args("a.jpg"))
        self.assertIn("png", image_output_args("a.png"))
        self.assertIn("libwebp", image_output_args("a.webp"))
        self.assertEqual(image_output_args("a.png")[:4], ["-frames:v", "1", "-update", "1"])


@unittest.skipUnless(HAS_QT, "PySide6 no está instalado")
class ToolsWithImagesTest(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile
        self.dir = tempfile.mkdtemp(prefix="tools_", dir=_env.TMP)
        for name in ("foto.jpg", "a.png", "v.mp4"):
            open(os.path.join(self.dir, name), "wb").close()

    def p(self, name):
        import os
        return os.path.join(self.dir, name)

    def check_image(self, job, out):
        cmd = job["commands"][0]
        self.assertNotIn("libx264", cmd)
        self.assertIn("-frames:v", cmd)
        self.assertEqual(cmd[-1], out)

    def test_rotar_imagen(self):
        out = self.p("foto_rotado.jpg")
        self.check_image(page_tools.b_rotate({"input": self.p("foto.jpg"), "op": "90"}, out), out)

    def test_rotar_video_sigue_igual(self):
        cmd = page_tools.b_rotate({"input": self.p("v.mp4"), "op": "90"}, self.p("v_rotado.mp4"))["commands"][0]
        self.assertIn("libx264", cmd)

    def test_encuadre_imagen(self):
        out = self.p("a_e.png")
        self.check_image(page_tools.b_crop_scale({"input": self.p("a.png"), "crop": "1:1", "height": ""}, out), out)


if __name__ == "__main__":
    unittest.main()

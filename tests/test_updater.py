import unittest

from tests import _env
from dvdy.config import APP_VERSION
from dvdy import updater
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


class LinuxUpdateTest(unittest.TestCase):
    ASSETS = [
        {"name": "DVDY_Studio-v2.4.0-windows-x64.zip", "browser_download_url": "z", "size": 1},
        {"name": "dvdy-studio_2.4.0_arm64.deb", "browser_download_url": "arm", "size": 2},
        {"name": "dvdy-studio_2.4.0_amd64.deb", "browser_download_url": "amd", "size": 3},
    ]

    def test_elige_el_deb_de_la_arquitectura(self):
        old = updater.deb_arch
        try:
            updater.deb_arch = lambda: "amd64"
            self.assertEqual(updater.pick_deb(self.ASSETS)["browser_download_url"], "amd")
            updater.deb_arch = lambda: "arm64"
            self.assertEqual(updater.pick_deb(self.ASSETS)["browser_download_url"], "arm")
            updater.deb_arch = lambda: "riscv64"
            self.assertIsNone(updater.pick_deb(self.ASSETS))
        finally:
            updater.deb_arch = old

    def test_el_zip_sigue_siendo_el_primero_para_windows_viejos(self):
        # Las versiones ya instaladas en Windows toman el primer archivo que termina en .zip
        self.assertEqual([a for a in self.ASSETS if a["name"].endswith(".zip")][0]["browser_download_url"], "z")

    def test_mensaje_si_se_cancela_la_contrasena(self):
        text, log = updater.update_failure_message("126:/tmp/x/actualizar.log")
        self.assertIn("contraseña", text)
        self.assertEqual(log, "/tmp/x/actualizar.log")
        text, _ = updater.update_failure_message("100:/tmp/x/actualizar.log")
        self.assertIn("No se pudo instalar", text)

    def test_mensaje_si_apt_estaba_ocupado(self):
        import os
        import tempfile
        fd, log = tempfile.mkstemp(dir=_env.TMP)
        with os.fdopen(fd, "w") as f:
            f.write("E: No se pudo bloquear /var/lib/dpkg/lock-frontend. Está siendo usado por aptd")
        text, _ = updater.update_failure_message(f"100:{log}")
        self.assertIn("otras actualizaciones", text)


if __name__ == "__main__":
    unittest.main()

import io
import os
import stat
import tarfile
import tempfile
import unittest
import zipfile

from tests import _env
from dvdy import deps, system


@unittest.skipIf(system.IS_WINDOWS, "carpetas XDG: solo Linux")
class XdgTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="home_", dir=_env.TMP)
        self.old = {k: os.environ.get(k) for k in ("HOME", "XDG_CONFIG_HOME")}
        os.environ["HOME"] = self.home
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.home, ".config")
        os.makedirs(os.environ["XDG_CONFIG_HOME"])

    def tearDown(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def write_dirs(self, text):
        with open(os.path.join(self.home, ".config", "user-dirs.dirs"), "w", encoding="utf-8") as f:
            f.write(text)

    def test_carpetas_en_espanol(self):
        os.makedirs(os.path.join(self.home, "Descargas"))
        os.makedirs(os.path.join(self.home, "Música"))
        self.write_dirs('# comentario\nXDG_DOWNLOAD_DIR="$HOME/Descargas"\nXDG_MUSIC_DIR="$HOME/Música"\n')
        self.assertEqual(system.user_dir("download"), os.path.join(self.home, "Descargas"))
        self.assertEqual(system.user_dir("music"), os.path.join(self.home, "Música"))

    def test_sin_user_dirs_usa_downloads_o_home(self):
        os.makedirs(os.path.join(self.home, "Downloads"))
        self.assertEqual(system.user_dir("download"), os.path.join(self.home, "Downloads"))
        self.assertEqual(system.user_dir("music"), self.home)

    def test_carpeta_inexistente_no_se_usa(self):
        self.write_dirs('XDG_DOWNLOAD_DIR="$HOME/NoExiste"\n')
        self.assertEqual(system.user_dir("download"), self.home)

    def test_config_y_datos(self):
        self.assertEqual(system.config_dir(), os.path.join(self.home, ".config", "dvdy-studio"))
        self.assertTrue(system.data_dir().endswith(os.path.join("data", "dvdy-studio")))


class ExtractTest(unittest.TestCase):
    """deps._extract: saca ffmpeg/ffprobe de un .zip (Windows) o .tar.xz (Linux)."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ext_", dir=_env.TMP)
        self.old_bin = deps.BIN_DIR
        deps.BIN_DIR = os.path.join(self.dir, "bin")

    def tearDown(self):
        deps.BIN_DIR = self.old_bin

    def names(self):
        return [f"ffmpeg-x/bin/ffmpeg{system.EXE_SUFFIX}", f"ffmpeg-x/bin/ffprobe{system.EXE_SUFFIX}", "ffmpeg-x/LICENSE"]

    def check(self, archive):
        deps._extract(archive, ("ffmpeg", "ffprobe"))
        for n in ("ffmpeg", "ffprobe"):
            p = os.path.join(deps.BIN_DIR, n + system.EXE_SUFFIX)
            with open(p, "rb") as f:
                self.assertEqual(f.read(), n.encode())
            if not system.IS_WINDOWS:
                self.assertTrue(os.stat(p).st_mode & stat.S_IXUSR, "debe quedar ejecutable")
        self.assertFalse(os.path.exists(os.path.join(deps.BIN_DIR, "license")))

    def test_zip(self):
        path = os.path.join(self.dir, "a.zip")
        with zipfile.ZipFile(path, "w") as z:
            for n in self.names():
                z.writestr(n, os.path.basename(n).split(".")[0])
        self.check(path)

    def test_tar_xz(self):
        path = os.path.join(self.dir, "a.tar.xz")
        with tarfile.open(path, "w:xz") as t:
            for n in self.names():
                data = os.path.basename(n).split(".")[0].encode()
                info = tarfile.TarInfo(n)
                info.size = len(data)
                t.addfile(info, io.BytesIO(data))
        self.check(path)

    def test_falta_un_programa(self):
        path = os.path.join(self.dir, "b.zip")
        with zipfile.ZipFile(path, "w") as z:
            z.writestr(f"x/ffmpeg{system.EXE_SUFFIX}", "ffmpeg")
        with self.assertRaises(RuntimeError):
            deps._extract(path, ("ffmpeg", "ffprobe"))

    def test_urls_del_sistema(self):
        u = deps.URLS
        if system.IS_WINDOWS:
            self.assertIn("win64", u["ffmpeg"])
            self.assertIn("windows", u["deno"])
        else:
            self.assertRegex(u["ffmpeg"], r"linux(64|arm64)-gpl\.tar\.xz$")
            self.assertIn("linux-gnu", u["deno"])


if __name__ == "__main__":
    unittest.main()


class ColorSchemeTest(unittest.TestCase):
    """Modo claro/oscuro de Ubuntu leído del portal (o de gsettings si el portal no responde)."""

    def setUp(self):
        self.saved = (system._run_text, system.shutil.which, system.IS_LINUX)
        system.IS_LINUX = True
        system.shutil.which = lambda name: "/usr/bin/" + name

    def tearDown(self):
        system._run_text, system.shutil.which, system.IS_LINUX = self.saved

    def fake(self, answers):
        def run(cmd, timeout=2):
            key = " ".join(cmd)
            for pattern, value in answers.items():
                if pattern in key:
                    return value
            return ""
        system._run_text = run

    def test_respuestas_del_portal(self):
        p = system.parse_portal_color_scheme
        self.assertEqual(p("(<uint32 1>,)"), 1)
        self.assertEqual(p("(<<uint32 2>>,)"), 2)
        self.assertIsNone(p(""))

    def test_portal_oscuro_y_claro(self):
        self.fake({"ReadOne": "(<uint32 1>,)"})
        self.assertEqual(system.linux_color_scheme(), "dark")
        self.fake({"ReadOne": "(<uint32 2>,)"})
        self.assertEqual(system.linux_color_scheme(), "light")

    def test_portal_viejo_solo_tiene_read(self):
        self.fake({"Settings.Read ": "(<<uint32 1>>,)"})
        self.assertEqual(system.linux_color_scheme(), "dark")

    def test_sin_portal_usa_gsettings(self):
        self.fake({"color-scheme": "'prefer-dark'"})
        system.shutil.which = lambda name: None if name == "gdbus" else "/usr/bin/" + name
        self.assertEqual(system.linux_color_scheme(), "dark")

    def test_sin_preferencia_mira_el_tema_gtk(self):
        self.fake({"ReadOne": "(<uint32 0>,)", "color-scheme": "'default'", "gtk-theme": "'Yaru-dark'"})
        self.assertEqual(system.linux_color_scheme(), "dark")
        self.fake({"ReadOne": "(<uint32 0>,)", "color-scheme": "'default'", "gtk-theme": "'Yaru'"})
        self.assertEqual(system.linux_color_scheme(), "light")

    def test_nada_responde(self):
        self.fake({})
        self.assertIsNone(system.linux_color_scheme())

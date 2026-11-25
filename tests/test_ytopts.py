import unittest

from tests import _env
from dvdy.ytopts import default_choices, title_filter


class TitleFilterTest(unittest.TestCase):
    def test_texto_literal_sin_mayusculas(self):
        f = title_filter("guns n' roses & co (live)")
        self.assertIsNone(f({"title": "GUNS N' ROSES & CO (LIVE) at Tokyo"}))
        self.assertIsNotNone(f({"title": "Otra banda"}))

    def test_caracteres_de_regex_no_son_especiales(self):
        f = title_filter("a.b")
        self.assertIsNotNone(f({"title": "axb"}))
        self.assertIsNone(f({"title": "a.b"}))

    def test_sin_titulo(self):
        f = title_filter("x")
        self.assertIsNone(f({}, incomplete=True), "en la lista plana se decide después")
        self.assertIsNotNone(f({}, incomplete=False))

    def test_combina_con_otro_filtro(self):
        base = lambda info, *, incomplete=False: None if info.get("duration", 0) >= 60 else "corto"  # noqa: E731
        f = title_filter("tema", base)
        self.assertIsNone(f({"title": "Tema 1", "duration": 120}))
        self.assertEqual(f({"title": "Tema 1", "duration": 10}), "corto")
        self.assertIsNotNone(f({"title": "Otro", "duration": 120}))


@unittest.skipUnless(_env.HAS_YTDLP, "yt-dlp no está instalado")
class BuildOptsTest(unittest.TestCase):
    def build(self, **over):
        from dvdy.ytopts import build_opts
        c = default_choices(audio=over.pop("audio", False))
        c.update(over)
        return build_opts(c)

    def keys(self, o):
        return [p["key"] for p in o["postprocessors"]]

    def test_video_mp4(self):
        o = self.build(quality="720")
        self.assertEqual(o["format"], "bv*+ba/b")
        self.assertIn("res:720", o["format_sort"])
        self.assertEqual(o["final_ext"], "mp4")
        self.assertIn("FFmpegVideoRemuxer", self.keys(o))

    def test_audio_mp3(self):
        o = self.build(audio=True)
        self.assertEqual(o["format"], "ba/b")
        self.assertEqual(o["final_ext"], "mp3")
        self.assertIn("FFmpegExtractAudio", self.keys(o))
        self.assertIn("EmbedThumbnail", self.keys(o))

    def test_filtro_de_titulo_con_apostrofo(self):
        o = self.build(title_filter="Guns N' Roses & más", min_duration="1:00")
        f = o["match_filter"]
        self.assertIsNone(f({"title": "guns n' roses & más - live", "duration": 300}, incomplete=False))
        self.assertIsNotNone(f({"title": "guns n' roses & más - live", "duration": 30}, incomplete=False))
        self.assertIsNotNone(f({"title": "otra", "duration": 300}, incomplete=False))

    def test_yt_dlp_acepta_el_filtro(self):
        import yt_dlp
        o = self.build(title_filter="Guns N' Roses")
        with yt_dlp.YoutubeDL({"quiet": True, "match_filter": o["match_filter"]}) as ydl:
            self.assertIsNone(ydl._match_entry({"id": "1", "title": "GUNS N' ROSES live"}, incomplete=False))
            self.assertIsNotNone(ydl._match_entry({"id": "2", "title": "Otra"}, incomplete=False))

    def test_tiempo_invalido(self):
        with self.assertRaises(ValueError):
            self.build(min_duration="uno")

    def test_fragmento(self):
        o = self.build(section=True, section_start="0:10", section_end="0:20")
        self.assertIn("download_ranges", o)


if __name__ == "__main__":
    unittest.main()

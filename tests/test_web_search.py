import unittest
from unittest import mock

from audio_to_lrc.aligner import align_lyrics_to_audio
from audio_to_lrc.web_search import extract_lyrics_lines_from_html


class WebSearchTests(unittest.TestCase):
    def test_parse_duckduckgo_html(self):
        html = '<html><body><a rel="nofollow" class="result__a" href="https://example.com/lyrics">Example Song Lyrics</a><a class="result__snippet">A lyric snippet</a></body></html>'
        from audio_to_lrc.web_search import search_web

        with mock.patch("audio_to_lrc.web_search.requests.get") as mocked_get:
            mocked_get.return_value.text = html
            mocked_get.return_value.raise_for_status.return_value = None
            results = search_web("example song lyrics")

        self.assertTrue(results)
        self.assertEqual(results[0]["title"], "Example Song Lyrics")
        self.assertEqual(results[0]["url"], "https://example.com/lyrics")

    def test_extract_lyrics_lines_from_html(self):
        html = """
        <html><body>
        <div class="lyrics">Hello world</div>
        <div class="lyrics">My darling</div>
        <div class="lyrics">Tonight</div>
        </body></html>
        """
        lines = extract_lyrics_lines_from_html(html)
        self.assertEqual(lines[:3], ["Hello world", "My darling", "Tonight"])

    def test_align_lyrics_to_audio(self):
        recognized = [
            (0.0, 1.0, "hello world"),
            (1.0, 2.0, "my darling"),
            (2.0, 3.0, "tonight"),
        ]
        official = ["Hello world", "My darling", "Tonight"]
        aligned = align_lyrics_to_audio(recognized, official)
        self.assertEqual([text for _, _, text in aligned], official)
        self.assertEqual(aligned[0][0], 0.0)


if __name__ == "__main__":
    unittest.main()

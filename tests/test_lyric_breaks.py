import unittest

from audio_to_lrc.lyric_breaks import split_lyrics_by_rhythm


class LyricBreakTests(unittest.TestCase):
    def test_split_long_line(self):
        lyrics = [
            (0.0, 3.0, "这是一个非常非常长的歌词行，几乎像一整句都挤在一起"),
        ]
        result = split_lyrics_by_rhythm(lyrics, max_chars=16, min_gap=1.5)
        self.assertGreaterEqual(len(result), 2)
        self.assertTrue(all(len(text) <= 24 for _, _, text in result))


if __name__ == "__main__":
    unittest.main()

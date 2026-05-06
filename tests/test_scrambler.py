import numpy as np
import pytest
from seed import Seed
from scrambler import scramble_image, descramble_image, _find_ffmpeg


class TestScramblerRoundTrip:
    def test_rgb_roundtrip_basic(self):
        img = np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)
        seed = Seed(1280, 720, 32, 12345)
        scrambled = scramble_image(img, seed)
        recovered = descramble_image(scrambled, seed)
        assert np.array_equal(img, recovered)

    def test_various_sizes_and_blocks(self):
        configs = [
            (720, 1280, 32),
            (1080, 1920, 16),
            (480, 640, 64),
            (600, 800, 8),
            (100, 100, 16),
        ]
        for h, w, bs in configs:
            img = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
            seed = Seed(w, h, bs, 42)
            scrambled = scramble_image(img, seed)
            recovered = descramble_image(scrambled, seed)
            assert np.array_equal(img, recovered), f"Failed for ({w}x{h}, bs={bs})"

    def test_grayscale(self):
        img = np.random.randint(0, 256, (720, 1280), dtype=np.uint8)
        seed = Seed(1280, 720, 32, 12345)
        scrambled = scramble_image(img, seed)
        recovered = descramble_image(scrambled, seed)
        assert np.array_equal(img, recovered)

    def test_rgba(self):
        img = np.random.randint(0, 256, (720, 1280, 4), dtype=np.uint8)
        seed = Seed(1280, 720, 32, 12345)
        scrambled = scramble_image(img, seed)
        recovered = descramble_image(scrambled, seed)
        assert np.array_equal(img, recovered)

    def test_small_image_no_full_blocks(self):
        # Image smaller than block size: cols=0 or rows=0, should return copy
        img = np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8)
        seed = Seed(10, 10, 32, 12345)
        scrambled = scramble_image(img, seed)
        recovered = descramble_image(scrambled, seed)
        assert np.array_equal(img, recovered)

    def test_edge_stripes_preserved(self):
        # 1280x720, bs=64 -> cols=20, rows=11, full_w=1280, full_h=704
        # Bottom stripe of 16px should be preserved
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        img[704:720, :, :] = 255  # white bottom stripe
        seed = Seed(1280, 720, 64, 999)
        scrambled = scramble_image(img, seed)
        # Bottom stripe should still be white (not moved)
        assert np.all(scrambled[704:720, :, :] == 255)
        recovered = descramble_image(scrambled, seed)
        assert np.array_equal(img, recovered)

    def test_deterministic(self):
        img = np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)
        seed = Seed(1280, 720, 32, 777)
        s1 = scramble_image(img, seed)
        s2 = scramble_image(img, seed)
        assert np.array_equal(s1, s2)

    def test_different_seeds_produce_different_results(self):
        img = np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)
        s1 = scramble_image(img, Seed(1280, 720, 32, 1))
        s2 = scramble_image(img, Seed(1280, 720, 32, 2))
        assert not np.array_equal(s1, s2)


class TestFindFfmpeg:
    def test_returns_string_or_none(self):
        result = _find_ffmpeg()
        assert result is None or isinstance(result, str)

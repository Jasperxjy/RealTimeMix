from seed import Seed


class TestSeedRoundTrip:
    def test_basic_roundtrip(self):
        seed = Seed(1280, 720, 32, 12345)
        s = seed.to_string()
        recovered = Seed.from_string(s)
        assert recovered is not None
        assert recovered.aspect_w == seed.aspect_w
        assert recovered.aspect_h == seed.aspect_h
        assert recovered.block_size == seed.block_size
        assert recovered.seed == seed.seed
        assert recovered.version == seed.version
        assert recovered.algorithm == seed.algorithm

    def test_various_dimensions(self):
        cases = [
            (1920, 1080, 16, 0),
            (640, 480, 64, 999999),
            (1, 1, 8, 2**63 - 1),
            (4096, 2160, 32, 0xDEADBEEF),
        ]
        for w, h, bs, val in cases:
            seed = Seed(w, h, bs, val)
            s = seed.to_string()
            recovered = Seed.from_string(s)
            assert recovered is not None, f"Failed for ({w}, {h}, {bs}, {val})"
            assert recovered.aspect_w == w
            assert recovered.aspect_h == h
            assert recovered.block_size == bs
            assert recovered.seed == val

    def test_invalid_empty_string(self):
        assert Seed.from_string("") is None
        assert Seed.from_string("   ") is None

    def test_invalid_garbage(self):
        assert Seed.from_string("!!!not-valid!!!") is None
        assert Seed.from_string("abc") is None

    def test_crc_tampering(self):
        seed = Seed(1280, 720, 32, 12345)
        s = seed.to_string()
        # Flip a character in the middle to corrupt CRC
        tampered = s[:5] + ("X" if s[5] != "X" else "Y") + s[6:]
        assert Seed.from_string(tampered) is None

    def test_padding_restored(self):
        # URL-safe base64 without padding
        seed = Seed(100, 100, 16, 42)
        s = seed.to_string()
        assert "=" not in s
        recovered = Seed.from_string(s)
        assert recovered is not None

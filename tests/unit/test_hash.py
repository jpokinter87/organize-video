"""Tests for hash utilities."""

import pytest
from pathlib import Path
from organize.utils.hash import checksum_md5


class TestChecksumMd5:
    """Tests for the checksum_md5() function."""

    def test_checksum_nonexistent_file(self, tmp_path):
        """Returns 'no_md5_hash' for nonexistent file."""
        nonexistent = tmp_path / "nonexistent.mkv"
        assert checksum_md5(nonexistent) == 'no_md5_hash'

    def test_checksum_small_file(self, tmp_path):
        """Small files (<650KB) are fully hashed."""
        small_file = tmp_path / "small.mkv"
        small_file.write_bytes(b"test content")

        result = checksum_md5(small_file)
        assert result != 'no_md5_hash'
        assert len(result) == 32  # MD5 hex digest is 32 chars

    def test_checksum_large_file(self, tmp_path):
        """Large files are partially hashed from middle."""
        large_file = tmp_path / "large.mkv"
        # Create a file larger than 650KB
        large_file.write_bytes(b"x" * 700000)

        result = checksum_md5(large_file)
        assert result != 'no_md5_hash'
        assert len(result) == 32

    def test_checksum_consistency(self, tmp_path):
        """Same file returns same hash."""
        file = tmp_path / "test.mkv"
        file.write_bytes(b"consistent content")

        hash1 = checksum_md5(file)
        hash2 = checksum_md5(file)
        assert hash1 == hash2

    def test_checksum_different_content(self, tmp_path):
        """Different content returns different hash."""
        file1 = tmp_path / "file1.mkv"
        file2 = tmp_path / "file2.mkv"
        file1.write_bytes(b"content one")
        file2.write_bytes(b"content two")

        hash1 = checksum_md5(file1)
        hash2 = checksum_md5(file2)
        assert hash1 != hash2

    def test_checksum_empty_file(self, tmp_path):
        """Empty file returns valid hash."""
        empty_file = tmp_path / "empty.mkv"
        empty_file.write_bytes(b"")

        result = checksum_md5(empty_file)
        assert result != 'no_md5_hash'
        assert len(result) == 32

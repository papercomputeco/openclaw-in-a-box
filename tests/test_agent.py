"""Tests for agent -- minimal repo analyzer agent."""
from pathlib import Path
from unittest.mock import patch

import pytest

from agent import analyze_directory, write_summary, main


@pytest.fixture
def sample_dir(tmp_path):
    (tmp_path / "hello.py").write_text("print('hello')\n")
    (tmp_path / "README.md").write_text("# Test Project\n\nA test.\n")
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "lib.py").write_text("def add(a, b):\n    return a + b\n")
    return tmp_path


def test_analyze_directory(sample_dir):
    result = analyze_directory(str(sample_dir))
    assert result["total_files"] == 3
    assert ".py" in result["extensions"]
    assert ".md" in result["extensions"]
    assert result["total_lines"] > 0


def test_analyze_empty_directory(tmp_path):
    result = analyze_directory(str(tmp_path))
    assert result["total_files"] == 0
    assert result["extensions"] == {}
    assert result["total_lines"] == 0


def test_write_summary(tmp_path, sample_dir):
    result = analyze_directory(str(sample_dir))
    output_path = tmp_path / "summary.md"
    write_summary(result, str(output_path))
    assert output_path.exists()
    content = output_path.read_text()
    assert "3" in content
    assert ".py" in content


def test_write_summary_creates_parent_dirs(tmp_path, sample_dir):
    result = analyze_directory(str(sample_dir))
    output_path = tmp_path / "nested" / "dir" / "summary.md"
    write_summary(result, str(output_path))
    assert output_path.exists()


def test_main_writes_output(sample_dir, tmp_path):
    output_file = tmp_path / "summary.md"
    with patch("sys.argv", ["agent.py", str(sample_dir), "--output", str(output_file)]):
        main()
    assert output_file.exists()


def test_main_invalid_directory(tmp_path):
    with patch("sys.argv", ["agent.py", str(tmp_path / "nonexistent")]):
        with pytest.raises(SystemExit):
            main()


def test_analyze_directory_with_unreadable_file(tmp_path):
    """Test that unreadable files are counted but lines are skipped."""
    (tmp_path / "hello.py").write_text("print('hello')\n")

    # Create a file that will raise an exception when read
    unreadable = tmp_path / "unreadable.txt"
    unreadable.write_text("test\n")

    # Mock the read_text to raise OSError for this file
    original_read = Path.read_text

    def mock_read(self, *args, **kwargs):
        if "unreadable" in str(self):
            raise OSError("Permission denied")
        return original_read(self, *args, **kwargs)

    with patch.object(Path, "read_text", mock_read):
        result = analyze_directory(str(tmp_path))
        assert result["total_files"] == 2
        assert result["total_lines"] >= 1  # At least from hello.py


def test_main_entry_point_runs(sample_dir, tmp_path):
    """Test that the if __name__ == '__main__' entry point executes."""
    output_file = tmp_path / "summary.md"
    # Import and run main directly (simulates __name__ == '__main__')
    from agent import main
    with patch("sys.argv", ["agent.py", str(sample_dir), "--output", str(output_file)]):
        main()
    assert output_file.exists()

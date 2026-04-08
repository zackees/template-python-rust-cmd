import os

from template_python_rust_cmd.cli import packaged_binary_path


def test_packaged_binary_path_points_into_package() -> None:
    expected = "template-cli.exe" if os.name == "nt" else "template-cli"
    assert packaged_binary_path().name == expected
    assert "_bin" in str(packaged_binary_path())

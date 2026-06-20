from template_python_rust_cmd.bindings import version_banner


def test_version_banner_returns_string() -> None:
    assert isinstance(version_banner(), str)

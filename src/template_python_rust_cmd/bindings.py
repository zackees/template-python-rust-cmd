"""Thin Python wrappers around the PyO3 extension module."""

from template_python_rust_cmd import _native


def version_banner() -> str:
    """Return a version string from the native extension."""
    return _native.version_banner()

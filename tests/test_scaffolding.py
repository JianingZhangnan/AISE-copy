"""Scaffold tests — verify package structure and entry point registration."""

import re


def test_package_importable():
    """导入 phycode 包的 __version__ 应是字符串且形如 0.1.0"""
    import phycode

    assert isinstance(phycode.__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+", phycode.__version__)


def test_cli_entrypoint_registered():
    """console_scripts 应包含 phycode 入口点且指向正确的模块路径"""
    import importlib.metadata as md

    eps = md.entry_points(group="console_scripts")
    matches = [ep for ep in eps if ep.name == "phycode"]
    assert matches, "phycode console_scripts entry point not registered"
    ep = matches[0]
    assert ep.value.startswith("phycode.cli.app")

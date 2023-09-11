import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runapi",
        action="store_true",
        help="Run tests that hit a drainable api resource",
    )

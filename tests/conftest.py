"""Pytest bootstrap that prevents optional external imports from reaching networks."""

from tests.fakes.external_modules import install_external_stubs

install_external_stubs()

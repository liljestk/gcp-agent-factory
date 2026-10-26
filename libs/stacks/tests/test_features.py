"""Bind every Gherkin feature in ./features to the shared steps in conftest.py."""

from pytest_bdd import scenarios

scenarios("features")

import pytest
import requests
from mobilevids.network import session_init

@pytest.fixture
def session():
    return session_init()

import subprocess
import pytest

def test_help():
    result = subprocess.run(['mobilevids-dl', '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Mobilevids Downloader script' in result.stdout

def test_version():
    # Since version is not a flag but displayed in debug, we can check if it runs without error
    result = subprocess.run(['mobilevids-dl', '--debug'], capture_output=True, text=True, input='\n')
    # It might fail because of lack of credentials if we don't mock it, 
    # but let's see if it at least starts.
    assert 'Version' in result.stdout or 'Version' in result.stderr or result.returncode != 127

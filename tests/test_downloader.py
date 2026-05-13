import pytest
import json
from mobilevids.downloader import Downloader
from mobilevids.define import SEARCH_URL

def test_downloader_search_single_result(session, requests_mock, monkeypatch, caplog):
    caplog.set_level("INFO")
    # Mock search response with a single result
    search_response = {
        "items": [
            {"id": 123, "title": "Single Movie", "cat_id": 1, "poster_thumbnail": "thumb.jpg"}
        ]
    }
    requests_mock.get(SEARCH_URL.format("user_id", "token", "query"), text=json.dumps(search_response))
    
    # Mock get_movie_by_id to avoid further network calls
    downloader = Downloader(session, "token", "user_id")
    
    # We expect it to call exit() if it finds a single result, so we catch SystemExit
    with monkeypatch.context() as m:
        m.setattr(downloader, "get_movie_by_id", lambda x: None)
        with pytest.raises(SystemExit):
            downloader.search("query")
    
    assert "Only one result found - downloading it!" in caplog.text

def test_get_quality():
    downloader = Downloader(None, None, None)
    info = {"src_vip_hd_1080p": "url1", "src_vip_hd": "url2"}
    assert downloader.get_quality(info) == "url1"
    
    info = {"src_vip_hd": "url2"}
    assert downloader.get_quality(info) == "url2"
    
    with pytest.raises(Exception, match="No video found for the given URL"):
        downloader.get_quality({})

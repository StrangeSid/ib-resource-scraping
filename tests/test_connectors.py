"""Phase: connectors. All HTTP mocked, no network."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ib_scrape.store import Store
from ib_scrape.connectors import mirror_api, wp_rest, ibnotes, ibdocs, tfm, drive, xtreme


def _resp(json_data=None, text="", status=200, headers=None):
    r = MagicMock()
    r.status_code = status
    r.headers = headers or {}
    r.json.return_value = json_data
    r.text = text
    r.content = text.encode()
    return r


def test_mirror_api_v3_first():
    s = MagicMock()
    s.get.return_value = _resp({"mirrors": [{"name": "m", "url": "https://x"}]})
    snap = mirror_api.snapshot(s)
    assert snap["mirrors"][0]["name"] == "m"
    assert snap["_api"].endswith("/v3/mirrors")


def test_mirror_api_retries_then_v2():
    s = MagicMock()
    err = ConnectionError("reset")
    ok = _resp({"mirrors": []})
    s.get.side_effect = [err, err, err, ok]
    snap = mirror_api.snapshot(s, retries=3)
    assert snap["_api"].endswith("/v2/mirrors")
    assert s.get.call_count == 4


def test_wp_iter_media_pagination():
    s = MagicMock()
    s.get.return_value = _resp([{"slug": "a"}], headers={"X-WP-TotalPages": "1"})
    items = list(wp_rest.iter_media(search="grade", session=s))
    assert [i["slug"] for i in items] == ["a"]
    assert "search" in s.get.call_args.kwargs["params"]


def test_wp_download_item(tmp_path):
    s = MagicMock()
    r = _resp()
    r.content = b"%PDF"
    s.get.return_value = r
    st = Store(tmp_path / "store")
    path, new = wp_rest.download_item(
        {"source_url": "http://x/f.pdf", "slug": "f", "mime_type": "application/pdf"},
        st, s)
    assert new and Path(path).read_bytes() == b"%PDF"


def test_ibnotes_extract_classify():
    s = MagicMock()
    s.get.return_value = _resp(text='<a href="https://drive.google.com/x">d</a>'
                                    '<a href="https://ibdocs.re/past-papers">p</a>'
                                    '<a href="/local">l</a>')
    links = ibnotes.extract(s)
    assert len(links) == 2
    assert links[0]["platform"] == "google_drive"
    assert ibnotes.census(links)[0]["count"] >= 1


def test_ibdocs_list_page():
    html = ('<a href="/IB%20X/Y" class="file-row"><span class="file-name">'
            '<span title="Y">Y</span></span><span class="file-size">-</span></a>'
            '<a href="/IB%20X/f.pdf" class="file-row"><span class="file-name">'
            '<span title="f.pdf">f</span></span><span class="file-size">1.2 MB</span></a>')
    s = MagicMock()
    s.get.return_value = _resp(text=html)
    rows = ibdocs.list_page("https://ibdocs.re/past-papers/2025/may-2025", s)
    assert rows[0]["is_dir"] and not rows[1]["is_dir"]
    assert rows[1]["url"].endswith("f.pdf")


def test_ibdocs_crawl_all_skips_404():
    import requests as rq
    s = MagicMock()

    def fake_get(url, timeout=30):
        if "may-2025" in url and "IB%20X" not in url:
            return _resp(text='<a href="/F" class="file-row"><span class="file-name">'
                              '<span title="F">F</span></span>'
                              '<span class="file-size">-</span></a>')
        if url == "https://ibdocs.re/F":
            return _resp(text="")
        r = _resp(status=404)
        r.raise_for_status.side_effect = rq.HTTPError("404")
        return r

    s.get.side_effect = fake_get
    recs = ibdocs.crawl_all(years=[2025], session=s, log=lambda *a: None)
    assert len(recs) == 1 and recs[0]["session"] == "may-2025"


def test_xtreme_list_dir():
    html = ('<a href="index.php?dirpath=./IB/X/&order=0" class="directory">[X]</a>'
            '<a href="IB/X/a_paper_1_TZ1_HL.pdf">f</a>')
    s = MagicMock()
    s.get.return_value = _resp(text=html)
    dirs, files = xtreme.list_dir("./IB/", s)
    assert dirs[0]["dirpath"] == "./IB/X/"
    assert files[0]["url"].endswith("a_paper_1_TZ1_HL.pdf")


def test_xtreme_crawl_bfs():
    pages = {"./IB/": ('<a href="index.php?dirpath=./IB/X/&order=0">[X]</a>', ""),
             "./IB/X/": ("", '<a href="IB/X/f.pdf">f</a>')}
    s = MagicMock()

    def fake_get(url, params=None, timeout=30):
        d, f = pages[params["dirpath"]]
        return _resp(text=d + f)

    s.get.side_effect = fake_get
    recs = xtreme.crawl("./IB/", s, log=lambda *a: None)
    assert len(recs) == 1 and recs[0]["source"] == "xtreme"


def test_tfm_403_needs_cookies():
    c = tfm.TFMClient("https://repo.pirateib.sh")
    c.s.get = MagicMock(return_value=_resp(status=403))
    try:
        c.list()
        raise AssertionError("should raise")
    except RuntimeError as e:
        assert "403" in str(e)


def test_tfm_list_parses_subpaths():
    c = tfm.TFMClient("https://repo.pirateib.sh")
    html = ('<a href="?p=IB+BOOKS">x</a> <input name="p" value="y">'
            '<a href="index.php?p=IB+DOCS&x=1">z</a>')
    c.s.get = MagicMock(return_value=_resp(text=html))
    subs = c.list("IB DOCUMENTS")
    assert "IB+BOOKS" in subs and "IB+DOCS" in subs


def test_wp_catalog_item():
    rec = wp_rest.catalog_item({"source_url": "http://x/f.pdf", "slug": "f",
                                "mime_type": "application/pdf",
                                "filesize": 42, "date": "2026-07-21T00:00:00"})
    assert rec["year"] == "2026" and rec["size"] == "42"


def test_drive_ids_and_export():
    assert drive.folder_id("https://drive.google.com/drive/folders/ABC123_-x") == "ABC123_-x"
    assert drive.file_id("https://drive.google.com/file/d/XYZ/view") == "XYZ"
    assert drive.export_url("XYZ").endswith("id=XYZ")
    import os
    os.environ.pop("DRIVE_API_KEY", None)
    try:
        drive.list_folder("ABC", api_key=None, session=MagicMock())
        raise AssertionError("should raise")
    except RuntimeError:
        pass

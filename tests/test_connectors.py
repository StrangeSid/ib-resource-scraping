"""Phase: connectors. All HTTP mocked, no network."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ib_scrape.store import Store
from ib_scrape.connectors import mirror_api, wp_rest, ibnotes, ibdocs, tfm, drive, xtreme, uc_harvest, dufs


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


def test_drive_download_direct_and_confirm(tmp_path):
    st = Store(tmp_path / "store")
    s = MagicMock()
    pdf = _resp(text="...", headers={"Content-Type": "application/pdf",
                                     "Content-Disposition": 'attachment; filename="q.pdf"'})
    pdf.content = b"%PDF"
    s.get.return_value = pdf
    path, new = drive.download_file("ABC", st, s)
    assert new and Path(path).name.endswith("q.pdf")
    # confirm interstitial then file
    inter = _resp(text="confirm=CF9x", headers={"Content-Type": "text/html"})
    s.get.side_effect = [inter, pdf]
    path2, _ = drive.download_file("DEF", st, s)
    assert s.get.call_count == 3  # 1 direct + interstitial + confirmed
    assert Path(path2).read_bytes() == b"%PDF"


def test_tfm_download(tmp_path):
    st = Store(tmp_path / "store")
    c = tfm.TFMClient("https://repo.pirateib.sh")
    r = _resp(text="x")
    r.content = b"data"
    c.s.get = MagicMock(return_value=r)
    path, new = c.download("IB/a.pdf", st)
    assert new and Path(path).name.endswith("a.pdf")


def test_tfm_cookie_dict():
    c = tfm.TFMClient("https://repo.pirateib.sh", cookie_dict={"cf_clearance": "abc"})
    assert c.s.cookies.get("cf_clearance") == "abc"


def test_tfm_custom_session_keeps_headers():
    s = MagicMock()
    s.headers = {"User-Agent": "REAL-UA"}
    s.cookies = {}
    c = tfm.TFMClient("https://repo.pirateib.sh", session=s)
    assert c.s.headers["User-Agent"] == "REAL-UA"


TFM_HTML = ('<tr> <td><a href="?p="><i class="fa fa-chevron"></i> ..</a></td></tr>'
            '<tr> <td data-sort=X> <a href="?p=ROOT+SUB" title="SUB">'
            '<i class="fa fa-folder-o"></i> SUB </a> </td></tr>'
            '<tr> <td data-sort=Y> <a href="?p=ROOT+SUB2">'
            '<i class="fa fa-folder-o"></i> SUB2 </a> </td></tr>'
            '<tr> <td data-sort="a.pdf"> <a href="?p=ROOT&amp;view=a.pdf" title="a.pdf">'
            '<i class="fa fa-file-pdf-o"></i> a.pdf </a> </td>'
            '<td data-order="b-100"><span>100 B</span></td>'
            '<td class="inline-actions"> <a title="Direct link"'
            ' href="https://h/ROOT/a.pdf"><i></i></a> </td> </tr>')


def test_tfm_list_full():
    c = tfm.TFMClient("https://h")
    c.s.get = MagicMock(return_value=_resp(text=TFM_HTML))
    rows = c.list_full("ROOT")
    assert len(rows) == 3
    d, d2, f = rows
    assert d["is_dir"] and d["path"] == "ROOT SUB" and d["size"] == 0
    assert d2["is_dir"] and d2["name"] == "SUB2" and d2["path"] == "ROOT SUB2"
    assert not f["is_dir"] and f["size"] == 100
    assert f["direct"] == "https://h/ROOT/a.pdf"


def test_tfm_crawl_downloads(tmp_path):
    c = tfm.TFMClient("https://h")
    pages = {"ROOT": TFM_HTML, "ROOT SUB": ""}
    c.s.get = MagicMock(side_effect=lambda u, **k: _resp(
        text=pages.get(k["params"]["p"], "")))
    dl_resp = _resp(text="x")
    dl_resp.content = b"PDF"

    def fake_get(u, **k):
        if "params" in k:
            return _resp(text=pages.get(k["params"]["p"], ""))
        return dl_resp

    c.s.get.side_effect = fake_get
    st = Store(tmp_path / "store")
    recs = c.crawl("ROOT", store=st, dl_limit=5, log=lambda *a: None)
    assert len(recs) == 3
    n = st.db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    assert n == 1


def test_uc_harvest_mocked():
    import sys as _sys

    class _SB:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            m = MagicMock()
            m.get_title.return_value = "pirateIB Repository"
            m.get_cookies.return_value = [{"name": "cf_clearance", "value": "C"}]
            return m

        def __exit__(self, *a):
            return False

    mod = MagicMock()
    mod.SB = _SB
    _sys.modules["seleniumbase"] = mod
    try:
        got = uc_harvest.harvest("https://repo.pirateib.sh", wait=0)
        assert got["cookies"] == {"cf_clearance": "C"}
        s = uc_harvest.cleared_session("https://repo.pirateib.sh",
                                       cookie_dict=got["cookies"])
        assert s.cookies.get("cf_clearance") == "C"
    finally:
        del _sys.modules["seleniumbase"]


def test_uc_harvest_no_clearance():
    import sys as _sys

    class _SB:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            m = MagicMock()
            m.get_title.return_value = "pirateIB Repository"
            m.get_cookies.return_value = []
            return m

        def __exit__(self, *a):
            return False

    mod = MagicMock()
    mod.SB = _SB
    _sys.modules["seleniumbase"] = mod
    try:
        try:
            uc_harvest.harvest("https://x", wait=0)
            raise AssertionError("should raise")
        except RuntimeError as e:
            assert "cf_clearance" in str(e)
    finally:
        del _sys.modules["seleniumbase"]


def test_xtreme_containment_and_max_pages():
    seen_pages = []

    def fake_get(url, params=None, timeout=30):
        dp = params["dirpath"]
        seen_pages.append(dp)
        if dp == "./IB/":
            return _resp(text='<a href="index.php?dirpath=./CAIE/&order=0">[C]</a>'
                              '<a href="index.php?dirpath=./IB/X/&order=0">[X]</a>')
        return _resp(text="")

    s = MagicMock()
    s.get.side_effect = fake_get
    recs = xtreme.crawl("./IB/", s, log=lambda *a: None)
    assert "./CAIE/" not in seen_pages and recs == []
    # max_pages respected
    seen_pages.clear()
    xtreme.crawl("./IB/", s, max_pages=1, log=lambda *a: None)
    assert seen_pages == ["./IB/"]


def test_xtreme_search_and_download(tmp_path):
    s = MagicMock()
    s.get.return_value = _resp(text='<a href="IB/X/paper.pdf">p</a>')
    hits = xtreme.search("./IB/X/", "paper", s)
    assert hits[0]["url"].endswith("paper.pdf")
    st = Store(tmp_path / "store")
    r = _resp(text="x")
    r.content = b"%PDF-1"
    s.get.return_value = r
    path, new = xtreme.download(hits[0]["url"], st, s)
    assert new and Path(path).read_bytes() == b"%PDF-1"


DUFS_JSON = {"href": "/IB BOOKS/", "paths": [
    {"path_type": "Dir", "name": "Sub", "mtime": 1, "size": 0},
    {"path_type": "File", "name": "b.pdf", "mtime": 2, "size": 50}]}


def test_dufs_list_and_crawl(tmp_path):
    from ib_scrape.store import Store
    root = MagicMock()
    root.json.return_value = DUFS_JSON
    root.status_code = 200
    sub = MagicMock()
    sub.json.return_value = {"href": "/x", "paths": []}
    sub.status_code = 200
    pdf = MagicMock()
    pdf.status_code = 200
    pdf.content = b"PDF"
    pdf.headers = {"Content-Type": "application/pdf"}
    s = MagicMock()
    # order: list_json, crawl root list, inline file download, subdir list
    s.get.side_effect = [root, root, pdf, sub]
    rows = dufs.list_json("https://h", "IB BOOKS", s)
    assert len(rows) == 2 and rows[0]["is_dir"] and not rows[1]["is_dir"]
    assert rows[1]["url"].endswith("b.pdf")
    st = Store(tmp_path / "store")
    recs = dufs.crawl("https://h", "IB BOOKS", session=s, store=st,
                      dl_limit=5, log=lambda *a: None)
    assert len(recs) == 2
    assert st.db.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 1


def test_dufs_crawl_uc_mocked():
    import sys as _sys
    pages = {
        "https://h/?json": {"paths": [
            {"path_type": "Dir", "name": "Sub", "size": 0},
            {"path_type": "File", "name": "b.pdf", "size": 7}]},
        "https://h/Sub?json": {"paths": []},
    }

    class _SB:
        def __init__(self, *a, **k):
            self.opened = []

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def open(self, url):
            self.opened.append(url)

        def sleep(self, n):
            pass

        def get_text(self, sel):
            import json as _j
            return _j.dumps(pages[self.opened[-1]])

    mod = MagicMock()
    mod.SB = _SB
    _sys.modules["seleniumbase"] = mod
    try:
        recs = dufs.crawl_uc("https://h", log=lambda *a: None)
        assert len(recs) == 2 and recs[0]["source"] == "dufs:https://h"
    finally:
        del _sys.modules["seleniumbase"]


def test_dufs_crawl_uc_flush(tmp_path):
    import sys as _sys
    import json as _j

    class _SB:
        def __init__(self, *a, **k):
            self.opened = []

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def open(self, url):
            self.opened.append(url)

        def sleep(self, n):
            pass

        def get_text(self, sel):
            return '{"paths": []}'

    mod = MagicMock()
    mod.SB = _SB
    _sys.modules["seleniumbase"] = mod
    try:
        out = tmp_path / "flush.json"
        recs = dufs.crawl_uc("https://h", manifest=str(out), log=lambda *a: None)
        assert recs == [] and _j.loads(out.read_text()) == []
    finally:
        del _sys.modules["seleniumbase"]


def test_uc_cleared_session_cookie_file(tmp_path):
    jar = tmp_path / "cookies.txt"
    jar.write_text("# Netscape HTTP Cookie File\n"
                   ".h\tTRUE\t/\tFALSE\t0\tcf_clearance\tZ\n")
    s = uc_harvest.cleared_session("https://h", cookie_file=str(jar))
    assert s.cookies.get("cf_clearance") == "Z"


def test_uc_cffi_session_offline():
    cr = pytest.importorskip("curl_cffi.requests")
    s = uc_harvest.cffi_session({"cookies": {"cf_clearance": "C"}, "ua": "UA-X"})
    assert s.cookies.get("cf_clearance", "") == "C" or \
        any(c.value == "C" for c in s.cookies)
    assert s.headers.get("User-Agent") == "UA-X"

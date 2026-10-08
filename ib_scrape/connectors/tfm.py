"""TinyFileManager (?p=) crawler. Needs clearance cookies for CF hosts.

Solve the challenge once in a normal browser, export cookies in Netscape
format, pass --cookies. Without valid cookies list() gets HTTP 403.
"""
import http.cookiejar as cj
import re
import requests
from .. import config


class TFMClient:
    def __init__(self, host, cookie_file=None):
        self.host = host.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update(config.UA)
        if cookie_file:
            jar = cj.MozillaCookieJar(cookie_file)
            jar.load(ignore_discard=True, ignore_expires=True)
            self.s.cookies.update({c.name: c.value for c in jar})

    def list(self, path=""):
        r = self.s.get(self.host + "/index.php", params={"p": path}, timeout=60)
        if r.status_code == 403:
            raise RuntimeError(f"403 on {self.host} — clearance cookies missing/expired")
        r.raise_for_status()
        # TFM addresses paths as ?p=<path> links + hidden <input name="p">
        subs = set(re.findall(r"[?&]p=([^\"'&]+)", r.text))
        subs.update(re.findall(r'name="p"\s+value="([^"]+)"', r.text))
        return sorted(subs)

    def download(self, remote_path, store, filename=None):
        r = self.s.get(self.host + "/" + remote_path.lstrip("/"), timeout=300)
        r.raise_for_status()
        name = filename or remote_path.rsplit("/", 1)[-1]
        return store.save(r.content, source="tfm:" + self.host,
                          url=self.host + "/" + remote_path, filename=name)

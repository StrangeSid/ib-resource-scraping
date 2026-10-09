"""Clearance via SeleniumBase UC (headless). Proven vs repo.pirateib.sh.

seleniumbase is a trial-only dep (heavy, not in requirements.txt).
Import is lazy so the rest of the package never needs it.
Harvested cookies drop straight into TFMClient(cookie_dict=...).
"""
from .. import config


def harvest(host, wait=25):
    try:
        from seleniumbase import SB
    except ImportError:
        raise RuntimeError("pip install seleniumbase (trial-only, not required)")
    host = host.rstrip("/")
    with SB(uc=True, headless=True) as sb:
        sb.open(host + "/")
        sb.sleep(wait)
        title = sb.get_title()
        if any(m in title for m in ("Just a moment", "Un instant",
                                    "security verification", "Vérification")):
            raise RuntimeError(f"challenge held: {title}")
        cookies = {c["name"]: c["value"] for c in sb.get_cookies()}
        ua = sb.execute_script("return navigator.userAgent")
    if "cf_clearance" not in cookies:
        raise RuntimeError("no cf_clearance harvested")
    return {"cookies": cookies, "ua": ua}


def cleared_session(host, cookie_dict=None, cookie_file=None, ua=None):
    import requests
    s = requests.Session()
    s.headers.update(config.UA)
    if ua:
        s.headers["User-Agent"] = ua
    if cookie_dict:
        jar = cookie_dict.get("cookies", cookie_dict)
        s.cookies.update(jar)
    if cookie_file:
        import http.cookiejar as cj
        jar = cj.MozillaCookieJar(cookie_file)
        jar.load(ignore_discard=True, ignore_expires=True)
        s.cookies.update({c.name: c.value for c in jar})
    return s


def cffi_session(harvested):
    """Chrome-TLS session bound to harvested cookies. Needs curl_cffi.

    requests alone gets 403 even with valid cookies (TLS binding);
    curl_cffi chrome impersonation returns 200. Proven vs repo.pirateib.sh.
    """
    try:
        from curl_cffi import requests as cr
    except ImportError:
        raise RuntimeError("pip install curl_cffi (trial-only, not required)")
    s = cr.Session(impersonate="chrome")
    if harvested.get("ua"):
        s.headers.update({"User-Agent": harvested["ua"]})
    s.cookies.update(harvested.get("cookies", {}))
    return s

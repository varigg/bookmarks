"""URL normalisation: an item's identity is its normalised URL.

Known tracking parameters and the fragment are stripped; scheme, host, path
and every other query parameter are kept exactly as given.
"""

from urllib.parse import urlsplit, urlunsplit

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_PARAMS = frozenset(
    {
        "fbclid",
        "gclid",
        "dclid",
        "gbraid",
        "wbraid",
        "msclkid",
        "yclid",
        "twclid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "_hsenc",
        "_hsmi",
        "mkt_tok",
        "vero_id",
        "oly_enc_id",
        "oly_anon_id",
    }
)


class InvalidUrl(ValueError):
    pass


def _is_tracking(pair: str) -> bool:
    name = pair.split("=", 1)[0].lower()
    return name in _TRACKING_PARAMS or name.startswith(_TRACKING_PREFIXES)


def normalise_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise InvalidUrl(f"not an http(s) URL: {url!r}")
    kept = [p for p in parts.query.split("&") if p and not _is_tracking(p)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "&".join(kept), ""))


def domain_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")

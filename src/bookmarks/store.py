"""Item records and the SQL that reads and writes them."""

import json
import re
import sqlite3
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

# An item's identity is its normalised URL: known tracking parameters and
# the fragment are stripped; scheme, host, path and every other query
# parameter are kept exactly as given.
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


def type_name(value: str) -> str:
    """A Type's name: trimmed and lowercase. Raises `ValueError` if blank."""
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value.lower()


def _is_tracking(pair: str) -> bool:
    name = pair.split("=", 1)[0].lower()
    return name in _TRACKING_PARAMS or name.startswith(_TRACKING_PREFIXES)


def normalise_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise InvalidUrl(f"not an http(s) URL: {url!r}")
    kept = [p for p in parts.query.split("&") if p and not _is_tracking(p)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "&".join(kept), ""))


_WAYBACK = "https://web.archive.org/web/{url}"


def archive_url(url: str) -> str:
    """The item's page on the Wayback Machine."""
    return _WAYBACK.format(url=url)


def domain_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")


@dataclass(frozen=True)
class Provenance:
    cli: str
    model: str
    prompt_hash: str
    at: str
    truncated: bool


@dataclass(frozen=True)
class Item:
    id: int
    url: str
    domain: str
    title: str
    type: str
    summary: str
    entities: list[str]
    note: str | None
    saved_at: str
    provenance: Provenance


def identity(url: str) -> str:
    """An item's identity is its normalised URL. Raises `InvalidUrl`."""
    return normalise_url(url)


class ItemExists(Exception):
    """The URL already has an item; the producer decides what that means."""


def item_from_row(row: sqlite3.Row) -> Item:
    return Item(
        id=row["id"],
        url=row["url"],
        domain=row["domain"],
        title=row["title"],
        type=row["type"],
        summary=row["summary"],
        entities=json.loads(row["entities"]),
        note=row["note"],
        saved_at=row["saved_at"],
        provenance=Provenance(
            cli=row["prov_cli"],
            model=row["prov_model"],
            prompt_hash=row["prov_prompt_hash"],
            at=row["prov_at"],
            truncated=bool(row["prov_truncated"]),
        ),
    )


def get_by_id(conn: sqlite3.Connection, item_id: int) -> Item | None:
    row = conn.execute("SELECT * FROM item WHERE id = ?", (item_id,)).fetchone()
    return item_from_row(row) if row is not None else None


def get_by_url(conn: sqlite3.Connection, url: str) -> Item | None:
    row = conn.execute("SELECT * FROM item WHERE url = ?", (identity(url),)).fetchone()
    return item_from_row(row) if row is not None else None


def insert_item(
    conn: sqlite3.Connection,
    *,
    url: str,
    title: str,
    type: str,
    summary: str,
    entities: list[str],
    note: str | None,
    saved_at: str,
    provenance: Provenance,
) -> int:
    """Add a complete item and adopt its Type if unseen; a merged-away type
    name is stored as the type it was merged into. Raises `ItemExists`.

    Runs inside the caller's transaction, if any."""
    url = identity(url)
    type = resolve_type(conn, type)
    try:
        item_id = conn.execute(
            "INSERT INTO item (url, domain, title, type, summary, entities, note, "
            "saved_at, prov_cli, prov_model, prov_prompt_hash, prov_at, "
            "prov_truncated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "RETURNING id",
            (
                url,
                domain_of(url),
                title,
                type,
                summary,
                json.dumps(entities),
                note,
                saved_at,
                provenance.cli,
                provenance.model,
                provenance.prompt_hash,
                provenance.at,
                int(provenance.truncated),
            ),
        ).fetchone()[0]
    except sqlite3.IntegrityError as exc:
        if get_by_url(conn, url) is None:
            raise
        raise ItemExists(url) from exc
    conn.execute("INSERT OR IGNORE INTO type (name) VALUES (?)", (type,))
    return item_id


def types_in_use(conn: sqlite3.Connection) -> list[str]:
    return list(type_counts(conn))


def type_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Every type, adopted or base, with its item count; unused types count 0."""
    rows = conn.execute(
        "SELECT type.name, COUNT(item.id) AS n FROM type "
        "LEFT JOIN item ON item.type = type.name GROUP BY type.name ORDER BY type.name"
    )
    return {r["name"]: r["n"] for r in rows}


def newest_items(conn: sqlite3.Connection, limit: int) -> list[Item]:
    rows = conn.execute(
        "SELECT * FROM item ORDER BY saved_at DESC, id DESC LIMIT ?", (limit,)
    )
    return [item_from_row(r) for r in rows]


def delete_item(conn: sqlite3.Connection, item_id: int) -> None:
    """Its embeddings and keyword index entries go with it (cascade, trigger)."""
    conn.execute("DELETE FROM item WHERE id = ?", (item_id,))


# ponytail: splits at the first ". ", "! " or "? "; an abbreviation like
# "e.g. " cuts early. Use a sentence splitter if ledes read badly.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s")


def lede(summary: str) -> str:
    """A summary is written lede-first: its first sentence stands alone."""
    return _SENTENCE_END.split(summary.strip(), maxsplit=1)[0]


def resolve_type(conn: sqlite3.Connection, name: str) -> str:
    """The type a name means now: its merge target if it was merged away."""
    row = conn.execute(
        "SELECT target FROM type_alias WHERE name = ?", (name,)
    ).fetchone()
    return row["target"] if row is not None else name


def merge_types(conn: sqlite3.Connection, source: str, into: str) -> int:
    """Move every item of `source` to `into` and make `source` an alias of it;
    an unseen `into` is a rename. Returns how many items moved.

    Raises `ValueError` for an unknown `source`, for `into` being `source` or
    a merged-away name. Runs inside the caller's transaction, if any."""
    source, into = type_name(source), type_name(into)
    if source == into:
        raise ValueError("cannot merge a type into itself")
    if conn.execute("SELECT 1 FROM type WHERE name = ?", (source,)).fetchone() is None:
        raise ValueError(f"no type named {source!r}")
    if resolve_type(conn, into) != into:
        raise ValueError(
            f"{into!r} was merged into {resolve_type(conn, into)!r}; merge into that"
        )
    # A rename keeps the base flag: the type is the same, only its name changes.
    conn.execute(
        "INSERT OR IGNORE INTO type (name, base) "
        "SELECT ?, base FROM type WHERE name = ?",
        (into, source),
    )
    moved = conn.execute(
        "UPDATE item SET type = ? WHERE type = ?", (into, source)
    ).rowcount
    conn.execute("UPDATE type_alias SET target = ? WHERE target = ?", (into, source))
    conn.execute("INSERT INTO type_alias (name, target) VALUES (?, ?)", (source, into))
    conn.execute("DELETE FROM type WHERE name = ?", (source,))
    return moved

"""Embed step and hybrid search through the core."""

import pytest

from bookmarks.search import Filters
from tests.factories import summarised_item
from tests.fakes import FakeEmbedder


@pytest.fixture
def corpus(service, clock):
    items = {}
    items["crdt"] = summarised_item(
        service,
        url="https://inkandswitch.com/local-first",
        title="Local-first software",
        summary="An essay arguing that collaborative apps can merge concurrent "
        "edits on each device and keep working offline.",
        entities=["Ink & Switch", "CRDT", "Automerge"],
    )
    clock.advance(days=30)
    items["bread"] = summarised_item(
        service,
        url="https://bakery.example.org/sourdough",
        title="A sourdough loaf for beginners",
        summary="A step-by-step recipe for baking sourdough bread in a home oven.",
        entities=["King Arthur Baking"],
        type="recipe",
        note="try this at the weekend",
    )
    clock.advance(days=30)
    items["repo"] = summarised_item(
        service,
        url="https://github.com/automerge/automerge/tree/main",
        title="automerge/automerge",
        summary="A library of data structures for building collaborative apps.",
        entities=["Automerge", "Rust", "WebAssembly"],
        type="repo",
    )
    clock.advance(days=30)
    items["tax"] = summarised_item(
        service,
        url="https://money.example.com/budget",
        title="Budgeting basics",
        summary="How to set a monthly budget and start investing your savings.",
        entities=["Vanguard"],
    )
    service.embed()
    return items


def _ids(result):
    return [hit.item.id for hit in result.hits]


def test_embed_covers_every_item_once(service, embedder, corpus):
    assert len(embedder.documents) == 4
    assert service.embed().embedded == 0


def test_embedded_text_is_title_summary_and_note_not_entities(embedder, corpus):
    bread = next(d for d in embedder.documents if "sourdough" in d)
    assert "A sourdough loaf for beginners" in bread
    assert "try this at the weekend" in bread
    assert "King Arthur" not in bread


def test_submissions_are_not_embedded(service, embedder, fetcher):
    fetcher.page("https://example.com/x", "gone", status=404)
    service.save("https://example.com/x")
    service.save("https://example.com/pending-forever")
    service.drain(limit=1)

    assert service.embed().embedded == 0
    assert embedder.documents == []


def test_changing_the_embedding_model_re_embeds_everything(
    make_service, corpus, embedder
):
    other = FakeEmbedder(model="other-model")
    service = make_service(embedder=other)

    assert service.embed().embedded == 4
    assert service.embed().embedded == 0


def test_a_new_summary_invalidates_the_vector(service, corpus):
    service.conn.execute(
        "UPDATE item SET summary = 'rewritten' WHERE id = ?", (corpus["tax"].id,)
    )
    assert service.embed().embedded == 1


def test_embed_failure_is_reported_not_raised(make_service, corpus):
    broken = FakeEmbedder(model="new-model")
    broken.fail("ollama unreachable at http://127.0.0.1:11434")
    report = make_service(embedder=broken).embed()
    assert report.embedded == 0
    assert "ollama unreachable" in report.error


def test_exact_entity_string_ranks_the_item_that_mentions_it(service, corpus):
    result = service.search("Vanguard")

    assert _ids(result)[0] == corpus["tax"].id
    assert result.hits[0].ranks["fts"] == 1


def test_entity_outranks_a_summary_mention(service, corpus):
    result = service.search("CRDT")
    assert _ids(result)[0] == corpus["crdt"].id


def test_loose_paraphrase_finds_the_item_via_the_vector_leg(service, corpus):
    result = service.search("syncing my notes across laptop plus phone")

    top = result.hits[0]
    assert top.item.id == corpus["crdt"].id
    assert "fts" not in top.ranks
    assert top.ranks["vector"] == 1


def test_the_note_is_searchable(service, corpus):
    assert _ids(service.search("weekend"))[0] == corpus["bread"].id


def test_callers_never_add_prefixes(service, embedder, corpus):
    service.search("anything at all")
    assert embedder.queries == ["anything at all"]


@pytest.mark.parametrize(
    "filters,expected",
    [
        (Filters(types=["repo"]), {"repo"}),
        (Filters(types=["Recipe", "repo"]), {"bread", "repo"}),
        (Filters(domain="github.com"), {"repo"}),
        (Filters(domain="example.com"), {"tax"}),
        (Filters(saved_after="2026-11-15"), {"repo", "tax"}),
        (Filters(saved_before="2026-10-15"), {"crdt"}),
    ],
)
def test_filters_narrow_candidates_before_both_legs(service, corpus, filters, expected):
    result = service.search("collaborative apps merge automerge budget", filters)

    names = {name for name, item in corpus.items() if item.id in _ids(result)}
    assert names == expected


def test_submissions_are_never_searched(service, corpus, fetcher):
    fetcher.page("https://example.com/dead", "gone", status=404)
    service.save("https://example.com/dead", title="Vanguard dead page")
    service.drain()
    service.save("https://example.com/new", title="Vanguard pending page")

    result = service.search("Vanguard")

    assert {hit.item.url for hit in result.hits} == {
        item.url for item in corpus.values()
    }


def test_results_carry_summary_entities_note_and_scores(service, corpus):
    hit = service.search("sourdough").hits[0]

    assert hit.item.summary.startswith("A step-by-step recipe")
    assert hit.item.entities == ["King Arthur Baking"]
    assert hit.item.note == "try this at the weekend"
    assert hit.score > 0
    assert set(hit.ranks) <= {"fts", "vector"}


def test_limit_defaults_to_10_and_caps_at_50(service, fetcher, summariser):
    for n in range(55):
        summarised_item(
            service,
            url=f"https://example.com/{n}",
            title=f"Note {n}",
            summary="Shared words about gardening.",
        )
    service.embed()

    assert len(service.search("gardening").hits) == 10
    assert len(service.search("gardening", limit=500).hits) == 50


def test_vector_leg_degrades_when_the_embedder_is_down(service, embedder, corpus):
    embedder.fail()

    result = service.search("Vanguard")

    assert result.legs == ["fts"]
    assert "vector leg skipped" in result.notes[0]
    assert _ids(result)[0] == corpus["tax"].id


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_query_is_rejected(service, query):
    with pytest.raises(ValueError):
        service.search(query)

"""resummarise queues refreshes for the normal drain; the item is never lost."""

import pytest

from bookmarks import cli
from bookmarks.embed import unembedded_count
from bookmarks.ingest.summarise import Prompt
from tests.factories import item_at, submission_at, summarised_item
from tests.fakes import FakeSummariser, summary_json

A = "https://a.example.com/one"
B = "https://b.test/two"
C = "https://a.example.com/three"


def _seed(service, url, **kw):
    return summarised_item(
        service, url=url, title=kw.pop("title", url), summary="Old summary.", **kw
    )


@pytest.fixture
def library(service, make_service):
    """A (old model), B (old model, repo), C (new model); returns the new-model core."""
    _seed(service, A, saved_at="2026-01-01T00:00:00Z", note="why I kept it")
    _seed(service, B, type="repo")
    current = make_service(summariser=FakeSummariser(model="new-model"))
    _seed(current, C)
    return current


def _queued(service):
    return {s.url for s in service.list_submissions()}


def test_stale_queues_only_items_written_by_another_model(library):
    assert library.resummarise(stale=True) == (2, 0)

    assert _queued(library) == {A, B}


def test_stale_also_catches_a_changed_prompt(library, make_service):
    reworded = make_service(
        summariser=FakeSummariser(model="new-model"),
        prompt=Prompt(text="reworded", hash="other"),
    )

    assert reworded.resummarise(stale=True, types=["article"]) == (2, 0)
    assert _queued(reworded) == {A, C}  # C: current model, older prompt


def test_item_by_id_or_url_type_domain_and_limit_select(library):
    item_id = item_at(library, A).id
    assert library.resummarise(item_id=item_id) == (1, 0)
    assert _queued(library) == {A}

    assert library.resummarise(types=["repo"]) == (1, 0)
    assert library.resummarise(domain="a.example.com") == (1, 1)  # A already queued
    assert _queued(library) == {A, B, C}

    assert library.resummarise(url=B) == (0, 1)


def test_limit_takes_the_stalest_first(library):
    library.resummarise(stale=True, limit=1)

    assert len(_queued(library)) == 1


def test_a_selector_is_required_and_an_item_stands_alone(library):
    with pytest.raises(ValueError, match="give"):
        library.resummarise()
    with pytest.raises(ValueError, match="combined"):
        library.resummarise(url=A, stale=True)
    with pytest.raises(ValueError, match="no such item"):
        library.resummarise(url="https://nowhere.test/x")


def test_a_successful_refresh_replaces_summary_and_provenance_keeping_the_rest(
    library, summariser
):
    before = item_at(library, A)
    library.summariser.script(summary_json(title="New", summary="A fresh summary."))
    library.resummarise(url=A)

    report = library.drain()

    after = item_at(library, A)
    assert report.summarised == 1
    assert (after.id, after.saved_at, after.note) == (
        before.id,
        before.saved_at,
        "why I kept it",
    )
    assert (after.title, after.summary) == ("New", "A fresh summary.")
    assert after.provenance.model == "new-model"
    assert submission_at(library, A) is None


def test_a_refreshed_item_is_embedded_again(library, embedder):
    library.embed()
    assert unembedded_count(library.conn, embedder.model) == 0
    library.summariser.script(summary_json(summary="A fresh summary."))
    library.resummarise(url=A)
    library.drain()

    assert unembedded_count(library.conn, embedder.model) == 1
    library.embed()
    assert "A fresh summary." in " ".join(embedder.documents)


def test_a_failed_refresh_keeps_the_old_summary(library, fetcher):
    from bookmarks.ingest.fetch import HttpResponse

    fetcher.script(A, HttpResponse(status=404, text="gone"))
    library.resummarise(url=A)

    report = library.drain()

    assert report.failed == 1
    assert submission_at(library, A) is None
    assert item_at(library, A).summary == "Old summary."
    assert library.status().failed == 0


def test_deleting_an_item_cancels_its_queued_refresh(library):
    library.resummarise(url=A)

    library.delete_item(url=A)

    assert submission_at(library, A) is None
    assert library.drain().summarised == 0
    assert item_at(library, A) is None


def test_deleting_an_item_while_it_is_summarising_does_not_bring_it_back(
    library, make_service
):
    class DeletesMidFlight(FakeSummariser):
        def submit(self, request):
            library.delete_item(url=A)
            return super().submit(request)

    flaky = make_service(summariser=DeletesMidFlight(model="new-model"))
    flaky.resummarise(url=A)

    flaky.drain()

    assert item_at(flaky, A) is None


def test_the_cli_reports_the_counts_and_refuses_no_selector(
    library, open_service, monkeypatch, capsys, tmp_path
):
    monkeypatch.setenv("BOOKMARKS_DB", str(tmp_path / "b.db"))
    monkeypatch.setattr(cli, "_service_opener", lambda settings: open_service)

    cli.main(["resummarise", "--item", A])
    assert "1 queued for the drain, 0 already queued" in capsys.readouterr().out

    with pytest.raises(SystemExit, match="give"):
        cli.main(["resummarise"])

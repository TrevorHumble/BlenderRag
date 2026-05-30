"""Integration smoke tests for the acquirers against real sources.

Marked ``network`` so they're deselected from the light CI run
(``pytest -m 'not network'``). Run them locally/nightly to catch upstream
breakage — e.g. a manual branch rename or a changed API zip URL when Blender
ships a new version. They assert each source still yields valid Documents.

Run: ``uv run pytest -m network``
"""

import itertools

import pytest

from blender_rag.acquire import (
    acquire_blendermcp,
    acquire_bpy_api,
    acquire_dev_docs,
    acquire_manual,
    acquire_release_notes,
)
from blender_rag.schema import Document, SourceType

pytestmark = pytest.mark.network


def _first_n(gen, n=50):
    return list(itertools.islice(gen, n))


@pytest.mark.parametrize(
    "acquire, expected_type",
    [
        (acquire_release_notes, SourceType.RELEASE_NOTES),
        (acquire_manual, SourceType.MANUAL),
        (acquire_bpy_api, SourceType.API),
        (acquire_dev_docs, SourceType.DEV_DOCS),
        (acquire_blendermcp, SourceType.BLENDERMCP),
    ],
)
def test_acquirer_yields_valid_documents(acquire, expected_type):
    docs = _first_n(acquire())
    assert docs, f"{acquire.__name__} produced no documents"
    for d in docs:
        assert isinstance(d, Document)
        assert d.source_type is expected_type
        assert d.text.strip()
        assert d.source_url.startswith("http")
        assert d.title

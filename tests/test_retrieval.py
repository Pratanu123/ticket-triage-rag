"""Retrieval quality against the real Chroma + Ollama embed model."""

from __future__ import annotations

from app.rag.retrieve import retrieve


def test_password_reset_query_hits_login_docs():
    chunks = retrieve("how do I reset my password", k=4)

    assert chunks, "expected at least one retrieved chunk"
    sources = {c.source for c in chunks}
    categories = {c.category for c in chunks}

    assert any("login" in s for s in sources) or "login" in categories, (
        f"expected login docs, got sources={sources} categories={categories}"
    )
    # Top hit should be login-related
    top = chunks[0]
    assert "login" in top.source or top.category == "login"
    assert 0.0 <= top.score <= 1.0


def test_2fa_query_prefers_login_2fa_doc():
    chunks = retrieve("how do I reset my 2FA authenticator", k=4)

    assert chunks
    sources = [c.source for c in chunks]
    assert "login-2fa.md" in sources, f"expected login-2fa.md in {sources}"


def test_empty_query_does_not_crash():
    assert retrieve("") == []
    assert retrieve("   ") == []


def test_nonsense_query_returns_low_relevance_or_empty():
    chunks = retrieve("xqztl purple mango subroutine zx91", k=4)

    # Chroma may still return nearest neighbors; they should not dominate as login/billing.
    assert isinstance(chunks, list)
    if chunks:
        # Scores should exist and be finite; do not require empty.
        assert all(isinstance(c.score, float) for c in chunks)
        # At least the query should not uniquely match a single category with high score.
        # Soft check: top score for nonsense is typically weaker than a clear login query.
        clear = retrieve("reset my password on CloudNova", k=1)
        if clear:
            assert chunks[0].score <= clear[0].score + 0.15

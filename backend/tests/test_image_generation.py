# tests/test_image_generation.py

import pytest
from app.models.enums import ContentStatus, ContentCategory

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _confirm_content(client, db_session, collection_id, entity_id, content_id):
    """Confirma un contenido vía API."""
    return await client.post(
        f"/api/v1/collections/{collection_id}/entities/{entity_id}"
        f"/contents/{content_id}/confirm"
    )


async def _create_confirmed_content(
    client,
    db_session,
    mock_rag_engine,
    mock_llm,
    collection_id,
    entity_id,
    category="backstory",
):
    """Genera y confirma un contenido, retorna su id."""
    gen = await client.post(
        f"/api/v1/collections/{collection_id}/entities/{entity_id}"
        f"/generate/{category}",
        json={"query": "Descripción detallada para generación de imagen"},
    )
    assert gen.status_code == 201
    content_id = gen.json()["id"]
    confirm = await _confirm_content(
        client, db_session, collection_id, entity_id, content_id
    )
    assert confirm.status_code == 200
    return content_id


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_img_01_generate_image_with_confirmed_content(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """IMG-01: Generar imagen con content_id confirmado retorna 200 con prompt."""
    content_id = await _create_confirmed_content(
        client,
        db_session,
        mock_rag_engine,
        mock_llm,
        sample_collection.id,
        sample_entity.id,
    )

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}"
        f"/entities/{sample_entity.id}/generate/image",
        json={"content_id": content_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["backend"] == "mock"
    assert data["visual_prompt"]
    assert data["token_count"] > 0
    assert data["token_count"] <= 150


@pytest.mark.anyio
async def test_img_02_prompt_token_count_within_bounds(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """IMG-02: El prompt generado no supera 150 tokens estimados."""
    content_id = await _create_confirmed_content(
        client,
        db_session,
        mock_rag_engine,
        mock_llm,
        sample_collection.id,
        sample_entity.id,
    )

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}"
        f"/entities/{sample_entity.id}/generate/image",
        json={"content_id": content_id},
    )

    data = response.json()
    assert data["token_count"] <= 150


@pytest.mark.anyio
async def test_img_03_generate_image_without_content_id_uses_latest_confirmed(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """IMG-03: Sin content_id usa el confirmed más reciente automáticamente."""
    await _create_confirmed_content(
        client,
        db_session,
        mock_rag_engine,
        mock_llm,
        sample_collection.id,
        sample_entity.id,
    )

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}"
        f"/entities/{sample_entity.id}/generate/image",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["prompt_source"] in ("content", "description")


@pytest.mark.anyio
async def test_img_04_no_confirmed_content_returns_422(
    client, mock_rag_engine, sample_collection, sample_entity
):
    """IMG-04: Sin ningún contenido confirmado retorna 422."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}"
        f"/entities/{sample_entity.id}/generate/image",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_img_05_pending_content_id_returns_422(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """IMG-05: Pasar content_id de contenido pending (no confirmed) retorna 422."""
    gen = await client.post(
        f"/api/v1/collections/{sample_collection.id}"
        f"/entities/{sample_entity.id}/generate/backstory",
        json={"query": "Historia del personaje para imagen"},
    )
    pending_id = gen.json()["id"]

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}"
        f"/entities/{sample_entity.id}/generate/image",
        json={"content_id": pending_id},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_img_06_prompt_contains_entity_name(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """IMG-06: El prompt visual contiene el nombre de la entidad."""
    content_id = await _create_confirmed_content(
        client,
        db_session,
        mock_rag_engine,
        mock_llm,
        sample_collection.id,
        sample_entity.id,
    )

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}"
        f"/entities/{sample_entity.id}/generate/image",
        json={"content_id": content_id},
    )

    assert sample_entity.name in response.json()["visual_prompt"]


@pytest.mark.anyio
async def test_img_07_response_is_mock_backend(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """IMG-07: En entorno de dev el backend es siempre mock."""
    content_id = await _create_confirmed_content(
        client,
        db_session,
        mock_rag_engine,
        mock_llm,
        sample_collection.id,
        sample_entity.id,
    )

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}"
        f"/entities/{sample_entity.id}/generate/image",
        json={"content_id": content_id},
    )

    assert response.json()["backend"] == "mock"
    assert response.json()["generation_ms"] == 0

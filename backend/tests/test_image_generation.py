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
    """IMG-01: Generar imagen con content_id confirmado retorna 201 con prompt."""
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

    assert response.status_code == 201
    data = response.json()
    assert data["backend"] == "mock"
    assert data["visual_prompt"]
    assert data["prompt_token_count"] > 0
    assert data["prompt_token_count"] <= 150


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
    assert data["prompt_token_count"] <= 150


@pytest.mark.anyio
async def test_img_03_prompt_source_is_valid_value(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """IMG-03: El prompt_source retornado es uno de los valores esperados."""
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

    assert response.status_code == 201
    valid_sources = {"content_direct", "content_sentences", "description", "name_only"}
    assert response.json()["prompt_source"] in valid_sources


@pytest.mark.anyio
async def test_img_04_nonexistent_content_id_returns_422(
    client, mock_rag_engine, sample_collection, sample_entity
):
    """IMG-04: content_id inexistente o no confirmado retorna 422."""
    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}"
        f"/entities/{sample_entity.id}/generate/image",
        json={"content_id": "00000000-0000-0000-0000-000000000000"},
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

    assert response.status_code == 201
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

    assert response.status_code == 201
    assert response.json()["backend"] == "mock"
    assert response.json()["generation_ms"] == 0


@pytest.mark.anyio
async def test_img_08_pending_content_error_has_business_message(
    client, db_session, mock_rag_engine, mock_llm, sample_collection, sample_entity
):
    """IMG-08: content pending retorna 422 con mensaje de regla de negocio."""
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
    assert "no está confirmado" in response.json()["detail"]


@pytest.mark.anyio
async def test_img_09_blocked_generated_content_returns_422(
    client,
    monkeypatch,
    db_session,
    mock_rag_engine,
    mock_llm,
    sample_collection,
    sample_entity,
):
    """IMG-09: Guardrail de salida bloquea contenido y retorna 422 semántico."""
    from app.core.exceptions import GeneratedContentBlockedError

    content_id = await _create_confirmed_content(
        client,
        db_session,
        mock_rag_engine,
        mock_llm,
        sample_collection.id,
        sample_entity.id,
    )

    def _raise_blocked(_text: str):
        raise GeneratedContentBlockedError()

    monkeypatch.setattr(
        "app.services.image_generation_service.check_generated_output", _raise_blocked
    )

    response = await client.post(
        f"/api/v1/collections/{sample_collection.id}"
        f"/entities/{sample_entity.id}/generate/image",
        json={"content_id": content_id},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "El contenido generado no está permitido."

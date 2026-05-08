import pytest


@pytest.mark.anyio
async def test_list_all_users_as_admin(client, db_session):
    """ADM-01: GET /admin/users como admin retorna 200 y respeta paginación."""
    from app.models.users import User

    admin = db_session.get(User, "test-user-id")
    admin.is_admin = True
    for i in range(3):
        db_session.add(
            User(id=f"user-{i}", username=f"user{i}", hashed_password="hash")
        )
    db_session.commit()

    response = await client.get("/api/v1/admin/users?page=1&page_size=2")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 4
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 2
    assert len(body["data"]) == 2


@pytest.mark.anyio
async def test_list_all_users_as_normal_user(client, db_session):
    """ADM-02: GET /admin/users como user normal retorna 403."""
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 403


@pytest.mark.anyio
async def test_list_all_users_as_deleted_admin(client, db_session):
    """ADM-05: GET /admin/users como admin soft-deleted retorna 403."""
    from app.models.users import User

    admin = db_session.get(User, "test-user-id")
    admin.is_admin = True
    admin.is_deleted = True
    db_session.commit()

    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 403


@pytest.mark.anyio
async def test_admin_delete_collection(client, db_session):
    """ADM-03: DELETE /admin/collections/{id} como admin retorna 204."""
    from app.models.users import User
    from app.models.collections import Collection

    admin = db_session.get(User, "test-user-id")
    admin.is_admin = True
    db_session.commit()

    col = Collection(name="To Delete", description="", owner_id="test-user-id")
    db_session.add(col)
    db_session.commit()
    db_session.refresh(col)

    response = await client.delete(f"/api/v1/admin/collections/{col.id}")
    assert response.status_code == 204


@pytest.mark.anyio
async def test_admin_delete_user(client, db_session):
    """ADM-04: DELETE /admin/users/{id} como admin retorna 204; usuario marcado is_deleted."""
    from app.models.users import User

    admin = db_session.get(User, "test-user-id")
    admin.is_admin = True
    db_session.commit()

    target = User(id="target-user-id", username="targetuser", hashed_password="hash")
    db_session.add(target)
    db_session.commit()

    response = await client.delete("/api/v1/admin/users/target-user-id")
    assert response.status_code == 204

    db_session.expire_all()
    deleted = db_session.get(User, "target-user-id")
    assert deleted.is_deleted is True


@pytest.mark.anyio
async def test_admin_cannot_delete_self(client, db_session):
    """ADM-06: DELETE /admin/users/{id} retorna 403 cuando el admin intenta eliminarse a sí mismo."""
    from app.models.users import User

    admin = db_session.get(User, "test-user-id")
    admin.is_admin = True
    db_session.commit()

    response = await client.delete("/api/v1/admin/users/test-user-id")
    assert response.status_code == 403

    db_session.expire_all()
    admin_after = db_session.get(User, "test-user-id")
    assert admin_after.is_deleted is False

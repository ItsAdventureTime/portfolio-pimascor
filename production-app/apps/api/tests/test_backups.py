from .conftest import sign_in


def test_backup_catalog_is_visible_to_admin_and_dcs_only(client):
    sign_in(client, "admin")
    assert client.get("/api/v1/backups").status_code == 200

    sign_in(client, "dcs")
    assert client.get("/api/v1/backups").status_code == 200

    sign_in(client, "mich")
    assert client.get("/api/v1/backups").status_code == 403

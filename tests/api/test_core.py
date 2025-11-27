from fastapi import status

from tests.api import client
from tests.api.helpers import create_core, delete_core
from tests.api.sample_data import XRAY_CONFIG as xray_config, SING_BOX_CONFIG as sing_box_config


def test_core_create(access_token):
    """Test that the core create route is accessible."""

    core = create_core(access_token, name="xray_config")
    assert core["config"] == xray_config
    assert core["name"] == "xray_config"
    assert core["core_type"] == "xray"
    for v in core["fallbacks_inbound_tags"]:
        assert v in {"fallback-A", "fallback-B"}
    assert len(core["fallbacks_inbound_tags"]) == 2
    assert len(core["exclude_inbound_tags"]) == 0
    delete_core(access_token, core["id"])


def test_core_update(access_token):
    """Test that the core update route is accessible."""

    core = create_core(access_token)
    response = client.put(
        url=f"/api/core/{core['id']}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "config": xray_config,
            "name": "xray_config_update",
            "exclude_inbound_tags": ["Exclude"],
            "fallbacks_inbound_tags": ["fallback-A", "fallback-B", "fallback-C", "fallback-D"],
            "core_type": "xray",
        },
        params={"restart_nodes": False},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["config"] == xray_config
    assert response.json()["name"] == "xray_config_update"
    assert response.json()["core_type"] == "xray"
    for v in response.json()["exclude_inbound_tags"]:
        assert v in {"Exclude"}
    for v in response.json()["fallbacks_inbound_tags"]:
        assert v in {"fallback-A", "fallback-B", "fallback-C", "fallback-D"}
    assert len(response.json()["fallbacks_inbound_tags"]) == 4
    assert len(response.json()["exclude_inbound_tags"]) == 1
    delete_core(access_token, core["id"])


def test_core_get(access_token):
    """Test that the core get route is accessible."""

    core = create_core(access_token)
    response = client.get(
        url=f"/api/core/{core['id']}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["config"] == xray_config
    assert response.json()["core_type"] == "xray"
    delete_core(access_token, core["id"])


def test_core_create_singbox(access_token):
    core = create_core(access_token, name="singbox_core", config=sing_box_config, fallbacks=[], core_type="sing_box")
    assert core["core_type"] == "sing_box"
    assert core["config"] == sing_box_config
    delete_core(access_token, core["id"])


def test_core_singbox_rejects_fallback(access_token):
    response = client.post(
        url="/api/core",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "config": sing_box_config,
            "name": "invalid_singbox",
            "core_type": "sing_box",
            "fallbacks_inbound_tags": ["fb"],
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_core_delete_1(access_token):
    """Test that the core delete route is accessible."""

    response = client.delete(
        url="/api/core/1", headers={"Authorization": f"Bearer {access_token}"}, params={"restart_nodes": True}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_core_delete_2(access_token):
    """Test that the core delete route is accessible."""

    core = create_core(access_token, name="xray_config")
    response = client.delete(
        url=f"/api/core/{core['id']}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_inbounds_get(access_token):
    """Test that the inbounds get route is accessible."""

    core = create_core(access_token)
    response = client.get(
        url="/api/inbounds",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    config_tags = [
        inbound["tag"] for inbound in xray_config["inbounds"] if inbound["tag"] not in ["fallback-B", "fallback-A"]
    ]
    response_tags = [inbound for inbound in response.json() if "<=>" not in inbound]
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0
    assert set(response_tags) == set(config_tags)
    delete_core(access_token, core["id"])

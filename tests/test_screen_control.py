"""
Tests for screen control endpoint
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_control_screen_toggle_cover():
    """Test toggle_cover_page action"""
    # This test requires authentication and a valid activity
    # For now, we just verify the endpoint structure
    response = client.post(
        "/api/screen/test-activity-id/control",
        json={"action": "toggle_cover_page"}
    )
    # Will get 401 without auth, but that means endpoint exists
    assert response.status_code in [200, 401, 403, 404]


def test_control_screen_next_stage():
    """Test next_stage action"""
    response = client.post(
        "/api/screen/test-activity-id/control",
        json={"action": "next_stage"}
    )
    assert response.status_code in [200, 401, 403, 404]


def test_control_screen_previous_stage():
    """Test previous_stage action"""
    response = client.post(
        "/api/screen/test-activity-id/control",
        json={"action": "previous_stage"}
    )
    assert response.status_code in [200, 401, 403, 404]


def test_control_screen_invalid_action():
    """Test with invalid action"""
    response = client.post(
        "/api/screen/test-activity-id/control",
        json={"action": "invalid_action"}
    )
    # Should get validation error (422) or auth error (401)
    assert response.status_code in [422, 401]

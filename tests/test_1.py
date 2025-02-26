import json
import pytest
import os

def test_health_check(client):
    """Test to ensure the /health route is working."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {"status": "healthy"}

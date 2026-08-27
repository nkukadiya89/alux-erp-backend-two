# conftest.py

import pytest
from rest_framework.test import APIClient

from user.models import User


@pytest.fixture
def api_client():
    client = APIClient()
    return client


@pytest.fixture
def api_base_url():
    return "/api/v1/"


@pytest.fixture
def user():
    user = User.objects.create(username="john", email="john@example.com")
    user.set_password("password@123")
    user.is_active = True
    user.is_superuser = True
    user.save()
    return user


@pytest.fixture
def token(user, api_client):
    response = api_client.post(
        "/get-token/",
        {"email": "john@example.com", "password": "password@123"},
        format="json",
    )
    assert response.status_code == 200
    token = response.data["data"]["access"]
    return token


@pytest.fixture
def authenticated_api_client(token, api_client):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client

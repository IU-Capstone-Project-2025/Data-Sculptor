import pytest
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from tests.JWT.JWT.jwt_operations import validate_token, get_token, check_data_fields, make_fake_jwt, get_decoded_token


@pytest.mark.asyncio
async def test_token_present(get_token):
    if not get_token:
        assert False
    assert True

@pytest.mark.asyncio
async def test_invalid_signature_token(get_token):
    await validate_token(get_token)
    assert True

@pytest.mark.asyncio
async def test_expired_token(get_token):
    await validate_token(get_token)

@pytest.mark.asyncio
async def test_data_fields(get_token):
    decoded = await get_decoded_token(get_token)
    await check_data_fields(decoded)
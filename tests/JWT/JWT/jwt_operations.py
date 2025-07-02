# import jwt
# import datetime
import datetime
import asyncio
import base64
import json

with open('public.pem', 'r') as a:
    PUBLICKEY = a.read()

with open('private.pem', 'r') as a:
    PRIVKEY = a.read()

payload = {
    "user": "Timofey",
    "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
}

import aiohttp
import pytest_asyncio
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, DecodeError

# Get KC public key
@pytest_asyncio.fixture
async def get_token():
    # keycloak_url = "https://keycloak.local/realms/App-Users/protocol/openid-connect/certs"
    # async with aiohttp.ClientSession() as session:
    #     async with session.get(keycloak_url) as response:
    #         response.raise_for_status()  # Если запрос не успешен, выбросит исключение
    #         keys = await response.json()
    #         public_key = keys['keys'][0]['x5c'][0]  # x5c содержит сертификат в формате PEM
    # ***REMOVED*** f"-----BEGIN CERTIFICATE-----\n{public_key}\n-----END CERTIFICATE-----"
    original = jwt.encode(payload, PRIVKEY, algorithm="RS256")
    falsified = await make_fake_jwt(original)
    return original


async def get_decoded_token(token):
    return jwt.decode(
            token,
            PUBLICKEY,
            algorithms=["RS256"],
            options={"verify_exp": True}
        )


async def make_fake_jwt(token: str):
    splitted = token.split('.')
    payload = base64.b64decode(splitted[1] + '==')
    payload_dict = json.loads(payload.decode())

    payload_dict["user"] = 'admin'
    falsified_payload = base64.b64encode(str(payload_dict).encode()).decode()
    splitted[1] = falsified_payload
    return '.'.join(chunk for chunk in splitted)


async def validate_token(token):
    try:
        await get_decoded_token(token)
    except DecodeError:
        raise ValueError("Invalid token signature")
    except ExpiredSignatureError:
        raise ValueError("Token has expired")
    except InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")
    

async def check_data_fields(decoded):
    for field in payload.keys():
        try:
            print(f"Testing field {field}: {decoded[field]}")
        except:
            raise ValueError(f"Field {field} is not found in token")
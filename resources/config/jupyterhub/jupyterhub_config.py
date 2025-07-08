import os
import sys
from dotenv import load_dotenv

HERE = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))

deploy_env = os.path.join(PROJECT_ROOT, 'deployment', 'marsel.env')
load_dotenv(deploy_env, override=True)

jhub_env = os.path.join(HERE, '.env')
load_dotenv(jhub_env, override=True)

c = get_config()
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'
c.DockerSpawner.image = 'jupyter/scipy-notebook'
c.DockerSpawner.remove = True

c.JupyterHub.authenticator_class = "shared-password"
c.SharedPasswordAuthenticator.user_password = os.getenv("SHARED_PASSWORD")
c.SharedPasswordAuthenticator.admin_password = os.getenv("ADMIN_PASSWORD")
c.Authenticator.allowed_users = {"developer"}
c.Authenticator.admin_users   = {"admin"}

# Startup tweaks
c.Spawner.start_timeout = 120
c.Spawner.http_timeout = 120
c.Spawner.debug = True

# Environment variables passed from docker-compose.yml
LLM_VALIDATOR_URL = os.getenv('LLM_VALIDATOR_URL')
URL_STATIC_ANALYZER = os.getenv("URL_STATIC_ANALYZER")
URL_LSP_SERVER = os.getenv("URL_LSP_SERVER")
if not LLM_VALIDATOR_URL or not URL_LSP_SERVER or not URL_STATIC_ANALYZER:
    raise RuntimeError("LLM_VALIDATOR_URL env var is not specified")

c.Spawner.environment = {
    'LLM_VALIDATOR_URL': LLM_VALIDATOR_URL,
    'URL_STATIC_ANALYZER':URL_STATIC_ANALYZER,
    'URL_LSP_SERVER':URL_LSP_SERVER

}


# from oauthenticator.generic import GenericOAuthenticator
#
# KEYLOCK_HOST = os.getenv("KEYLOCK_HOST")
# JUPYTERHUB_HOST = os.getenv("JUPYTERHUB_HOST")
#
# c.JupyterHub.authenticator_class = GenericOAuthenticator
#
# c.GenericOAuthenticator.client_id = 'jupyterhub'
# c.GenericOAuthenticator.client_secret = 'SgWlrwMEvOdQ5N4jlheipE8us91DHzMI'
# c.GenericOAuthenticator.oauth_callback_url = f'http://{JUPYTERHUB_HOST}/hub/oauth_callback'
#
# c.GenericOAuthenticator.authorize_url = f'http://{KEYLOCK_HOST}/realms/App-Users/protocol/openid-connect/auth'
# c.GenericOAuthenticator.token_url = f'http://{KEYLOCK_HOST}/realms/App-Users/protocol/openid-connect/token'
# c.GenericOAuthenticator.userdata_url = f'http://{KEYLOCK_HOST}/realms/App-Users/protocol/openid-connect/userinfo'
#
# c.GenericOAuthenticator.username_key = 'preferred_username'
# c.GenericOAuthenticator.scope = ['openid', 'profile', 'email']

from dockerspawner import DockerSpawner
from oauthenticator.generic import GenericOAuthenticator
from tornado.web import HTTPError
#from jupyter_helper_classes import MyDockerSpawner
import logging
***REMOVED***
import os

logging.basicConfig(level=logging.DEBUG)

PROTO = "http"
JH_DOMAIN = os.getenv("JUPYTERHUB_DOMAIN_NAME")
JH_PORT = os.getenv("JUPYTERHUB_PORT_INTERNAL")
logging.info(f"starting on {JH_DOMAIN}:{JH_PORT}")
c = get_config()

logging.info(f"Secret of {os.getenv('CLIENT_ID')} is {os.getenv('CLIENT_SECRET')}")

# Setup Generic authenticator yoo
c.JupyterHub.authenticator_class = GenericOAuthenticator
c.GenericOAuthenticator.enable_auth_state = True
c.GenericOAuthenticator.client_id = os.getenv("CLIENT_ID")
c.GenericOAuthenticator.client_secret = os.getenv("CLIENT_SECRET")
c.GenericOAuthenticator.oauth_callback_url = os.getenv("OAUTH_CALLBACK_URL")
c.GenericOAuthenticator.authorize_url = os.getenv("AUTH_URL")
c.GenericOAuthenticator.token_url = os.getenv("TOKEN_URL")
c.GenericOAuthenticator.userdata_url = os.getenv("USERDATA_URL")

c.GenericOAuthenticator.userdata_token_method = "Bearer"
c.GenericOAuthenticator.username_claim = 'preferred_username'
c.GenericOAuthenticator.scope = ['openid', 'profile', 'email']

async def get_auth_state(auth_state):
    auth_state_data = auth_state.get("auth_state")
    if not auth_state_data:
        auth_state_data = auth_state
    return auth_state_data

# Check if user in JH group
async def post_auth_hook(authenticator, handler, auth_state):
    auth_state_data = await get_auth_state(auth_state)
    if not auth_state_data:
        logging.error("No auth_state data")
***REMOVED***

    oauth_user = auth_state_data.get("oauth_user")
    role = oauth_user.get("jupyterhub-role")
    logging.info(f"logged {role}, auth state: {oauth_user}")

    if role not in ["user", "admin"]:
        logging.error(f"Access for {oauth_user} denied")
        raise HTTPError(403, f"Access denied. Invalid role: {role}")
    
    user_mail = oauth_user.get("email")
    if not user_mail:
        raise HTTPError(401, f"Email are not present")
    
    # Clean_username are composed from email
    clean_username = user_mail.replace('@', '-').replace('.', '-')
    oauth_user["jupyterhub_username"] = clean_username
    auth_state["oauth_user"] = oauth_user
    
    auth_state["name"] = clean_username

    logging.debug(f"Received: {auth_state}")
    if role == "admin":
        logging.debug(f"New admin {clean_username} added")
        authenticator.admin_users.add(clean_username)

    return auth_state


c.GenericOAuthenticator.allow_all = True
c.GenericOAuthenticator.post_auth_hook = post_auth_hook
c.GenericOAuthenticator.refresh_pre_spawn = True

c.JupyterHub.spawner_class = DockerSpawner
c.DockerSpawner.image = 'jupyter/base-notebook'
c.DockerSpawner.remove = False
c.DockerSpawner.network_name = 'jupyter-network'
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.name_template = 'jupyter-{username}'
c.DockerSpawner.debug = True
c.DockerSpawner.docker_host = 'unix:///var/run/docker.sock'


# Subdomain proxy
c.JupyterHub.bind_url = f'{PROTO}://0.0.0.0:8000'
c.JupyterHub.hub_connect_ip = JH_DOMAIN
c.JupyterHub.subdomain_host = f'{PROTO}://{JH_DOMAIN}'
c.JupyterHub.db_url = 'sqlite:////srv/jupyterhub/jupyterhub.sqlite'
c.JupyterHub.allow_named_servers = True
c.JupyterHub.redirect_to_server = False
c.JupyterHub.cookie_domain = f'.{JH_DOMAIN}'
c.JupyterHub.trusted_downstream_ips = ['0.0.0.0/0']


c.JupyterHub.tornado_settings = {
    'headers': {
        'Access-Control-Allow-Origin': f'{PROTO}://{JH_DOMAIN}:{JH_PORT}',
        'Access-Control-Allow-Credentials': 'true',
    }
}


c = get_config()

c.JupyterHub.authenticator_class = "shared-password"

# Specify your developer password (actual user)
c.SharedPasswordAuthenticator.user_password = "reallygoodpassword"
c.Authenticator.allowed_users = {"developer"}

# Specify your admin password
c.Authenticator.admin_users = {"admin"}
c.SharedPasswordAuthenticator.admin_password = "really-super-good-admininstrator-password"

c.Spawner.start_timeout = 120
c.Spawner.http_timeout = 120
c.Spawner.debug = True

# Environment variables passed from docker-compose.yml
import os

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

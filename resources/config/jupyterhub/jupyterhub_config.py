from dotenv import load_dotenv
import os 

c = get_config()

c.JupyterHub.authenticator_class = "shared-password"

# add passwords into .env file
c.SharedPasswordAuthenticator.user_password = os.getenv("SHARED_PASSWORD")
c.SharedPasswordAuthenticator.admin_password = os.getenv("ADMIN_PASSWORD")

c.Authenticator.allowed_users = {"developer"}
c.Authenticator.admin_users = {"admin"}

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

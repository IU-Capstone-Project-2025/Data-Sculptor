c = get_config()

#c.Spawner.env = os.environ.copy()
c.Spawner.env = {
        'LLM_VALIDATOR_URL': 'localhost:9001'
}
c.JupyterHub.authenticator_class = "shared-password"

c.SharedPasswordAuthenticator.user_password = "reallygoodpassword"
c.Authenticator.allowed_users = {"developer"}

c.Authenticator.admin_users = {"admin"}
c.SharedPasswordAuthenticator.admin_password = "really-super-good-admininstrator-password"

c.Spawner.start_timeout = 120
c.Spawner.http_timeout = 120
c.Spawner.debug = True


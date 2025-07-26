from jupyterhub.handlers import BaseHandler
from jupyterhub.handlers.pages import SpawnHandler
from tornado import web
from jupyterhub.handlers import pages
import logging
import sys
logging.basicConfig(
    
    level=logging.INFO,
    format = "%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout
    
)

class CustomSpawnHandler(SpawnHandler):
    
    """
    This class should solve the problem with passing case_id from frontend (26.07.25 the feature is not implemented and tested yet).  
    But handler was not integrated into JupyterHub. Consider to delete it.
    """
    
    async def prepare(self):
        await super().prepare()          
        await self._capture_case_id()   

    async def _capture_case_id(self):
        case_id = self.get_argument("case_id", None)
        if case_id:
            auth = await self.current_user.get_auth_state() or {}
            auth["case_id"] = case_id
            await self.current_user.save_auth_state(auth)
            logging.info(f"Set case_id {case_id} for user {self.current_user.username}")
        else:
            logging.info(f"NO CASE ID WAS PROVIDED")
    # get/post не трогаем: наследуются как есть


# monkey patch
pages.SpawnHandler = CustomSpawnHandler

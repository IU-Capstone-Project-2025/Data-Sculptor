import os
from dockerspawner import DockerSpawner
from dotenv import load_dotenv
from minio import Minio
import subprocess
import logging
import sys
import asyncio
load_dotenv()

host = os.getenv("HOST_IP")
minio_port = os.getenv("MINIO_PORT_EXTERNAL")

endpoint = f"{host}:{minio_port}"
access_key = os.getenv("MINIO_ROOT_USER")
secret_key = os.getenv("MINIO_ROOT_PASSWORD")
client = Minio(endpoint, access_key=access_key, secret_key=secret_key)

logging.basicConfig(
    
    level=logging.INFO,
    format = "%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout
    
)

class CustomDockerSpawner (DockerSpawner):
    
    """
    In Parent start method, first checks image from config, then checks image from db.
    So REMOVE image from config!
    TODO:?
    """
    async def start(self):
        case_id = await self._get_case_id()
        path = await asyncio.to_thread( self._get_image_from_db, case_id)
        response = await asyncio.to_thread(self._load_image, path)
        os.remove(path) 
        self.image = await asyncio.to_thread(self._get_image_name, response)
        return await super().start()
    
    async def stop(self, now=False):
        return await super().stop(now)
    async def poll(self):
        return await super().poll()


    async def _get_case_id(self) -> str:
        auth = self.user.auth_state
        if not auth:
            logging.error("No authentication state found for user.")
            raise RuntimeError("No authentication state found for user.")
        case_id = auth.get("case_id")
        if not case_id:
            logging.error("No case_id found in authentication state.")
            raise RuntimeError("No case_id found in authentication state.")
        logging.info(f"Case ID retrieved: {case_id}")
        return case_id
    def _load_image(self, img_path) -> str:
        try:
            
            res = subprocess.run( ["docker", "load", "-i", img_path],
                check=True,
                text=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to load Docker image: {e}")
        logging.info(f"Image {id} loaded successfully.")
        return res.stdout
    
    def _get_image_name(self, output: str) -> str:
        for line in output.splitlines():
            line.strip()
            if line.startswith("Loaded image: "):
                return line.split("Loaded image: ")[1].strip()
        raise ValueError("Image name not found in output.")
                
        
    def _get_image_from_db(self, case_id) -> str:
        response = client.get_object(f"{case_id}", "image")
        path = f"/tmp/img_{id}.tar"
        try:
            with open(path, "wb") as img:
                for chunk in response.stream(32 * 1024):
                    img.write(chunk)
        finally:
            response.close()
            response.release_conn()
        return path
    

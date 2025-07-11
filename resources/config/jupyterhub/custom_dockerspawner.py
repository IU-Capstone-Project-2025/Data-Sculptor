import os
from dockerspawner import DockerSpawner
from dotenv import load_dotenv
from minio import Minio
import subprocess
import logging
import sys

load_dotenv()

endpoint = os.getenv("MINIO_ENDPOINT")
access_key = os.getenv("MINIO_ACCESS_KEY")
secret_key = os.getenv("MINIO_SECRET_KEY")
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
    TODO: ОТКУДА БЕРЕМ ID И ТОКЕН?
    """
    async def start(self):
        img_name = self._load_image(id, self.user.token)
        self.image = img_name
***REMOVED*** super().start()
    
    async def stop(self, now=False):
***REMOVED*** super().stop(True)
    async def poll(self):
***REMOVED*** super().poll()

    def _load_image(self, id, token) -> str:
        img_path = self._get_image_from_db(id, token)
        try:
            
            res = subprocess.run( ["docker", "load", "-i", img_path],
                check=True,
                text=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to load Docker image: {e}")
        logging.info(f"Image {id} loaded successfully.")
        img_name = self._get_image_name(res.stdout)
***REMOVED*** img_name
    
    def _get_image_name(self, output: str) -> str:
        for line in output.splitlines():
            line.strip()
            if line.startswith("Loaded image: "):
        ***REMOVED*** line.split("Loaded image: ")[1].strip()
        raise ValueError("Image name not found in output.")
                
        
    def _get_image_from_db(self, id, token) -> str:
        response = client.get_object(token, id)
        path = f"/tmp/img_{id}.tar"
        try:
            with open(path, "wb") as img:
                for chunk in response.stream(32 * 1024):
                    img.write(chunk)
        finally:
            response.close()
            response.release_conn()
***REMOVED*** path
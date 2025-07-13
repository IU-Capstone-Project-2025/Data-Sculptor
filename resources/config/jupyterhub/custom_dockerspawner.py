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
    template_path = None
    async def start(self):
        img_path: str | None = None 
        try:
            case_id =  self._get_case_id()
            img_path  = await asyncio.to_thread(self._get_image, case_id) 
            self.template_path = await asyncio.to_thread(self._get_template, case_id)
            response = await asyncio.to_thread(self._load_image, img_path)
            self.image = await asyncio.to_thread(self._get_image_name, response)
            self.volumes = {self.template_path: f"/home/jovyan/template_solution.ipynb"}
            return await super().start()
        except Exception as e:
            logging.error(f"Error during start: {e}")
            raise e
        finally:
            if img_path and os.path.exists(img_path):
                os.remove(img_path) 
    
    def _save_progress(self):
        bucket = f"progress-{self.user.id}"
        key =  "template"
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            client.fput_object(bucket, key, self.template_path)
        except Exception as e:
            logging.error(f"Failed to save progress: {e}")
        finally:
            if os.path.exists(self.template_path):
                os.remove(self.template_path)
        
    async def stop(self, now=False):
        try:
            await asyncio.to_thread(self._save_progress)
        except Exception as e:
            logging.error(f"Error saving progress: {e}")
        finally:
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
        except subprocess.CalledProcessError as  e:
            raise RuntimeError(f"Failed to load Docker image: {e}")
        logging.info(f"Image {img_path} loaded successfully.")
        return res.stdout
    
    def _get_image_name(self, output: str) -> str:
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("Loaded image: "):
                return line.split("Loaded image: ")[1].strip()
        raise ValueError("Image name not found in output.")
                
    
    def _get_image(self, case_id: str):
        img_path = f"/tmp/img_{self.user.id}_{case_id}.tar"
        img_path = self._get_data_from_db(case_id, "image", img_path)
        return img_path
    
    def _get_template(self, case_id):
        template_path = f"/tmp/template_{self.user.id}_{case_id}.ipynb"
        if client.bucket_exists(f"progress-{self.user.id}"):
            template_path = self._get_data_from_db(f"progress-{self.user.id}", "template", template_path)
        else:
            template_path  = self._get_data_from_db(f"{case_id}", "template", template_path)
        return template_path  
        
    def _get_data_from_db(self, bucket, key, file_to_save) -> str:
        response = client.get_object(f"{bucket}", f"{key}")
        
        try:
            with open(file_to_save, "wb") as img:
                for chunk in response.stream(32 * 1024):
                    img.write(chunk)
        finally:
            response.close()
            response.release_conn()
        return file_to_save

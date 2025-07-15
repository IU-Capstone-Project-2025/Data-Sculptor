import os
from dockerspawner import DockerSpawner
from dotenv import load_dotenv
from minio import Minio
import subprocess
import logging
import sys
import asyncio
import docker

load_dotenv()
import re

host = os.getenv("HOST_IP")
minio_port = os.getenv("MINIO_PORT_EXTERNAL")

endpoint = f"{host}:{minio_port}"
access_key = os.getenv("MINIO_ROOT_USER")
secret_key = os.getenv("MINIO_ROOT_PASSWORD")
# client = Minio(
#     "31.56.227.36:52298", access_key="minioadmin", secret_key="minioadmin", secure=False
# )
client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)


class CustomDockerSpawner(DockerSpawner):
    """
    In Parent start method, first checks image from config, then checks image from db.
    So REMOVE image from config!
    TODO: убрать захардкоженные креды minio, case_id
    """

    template_path = None
    feedback_path = None
    case_id= None
    async def start(self):
        img_path: str | None = None
        try:
            self.case_id = "1"

            logging.info("Getting image from DB")
            img_path = await asyncio.to_thread(self._get_image, self.case_id)
            logging.info(f"Image path: {img_path}")

            logging.info("Getting template")
            self.template_path = await asyncio.to_thread(self._get_template, self.case_id)
            logging.info(f"Template path: {self.template_path}")

            logging.info("Getting feedback")
            self.feedback_path = await asyncio.to_thread(self._get_feedback, self.case_id)
            logging.info(f"Feedback path: {self.feedback_path}")

            logging.info("loading image to local docker repoitory")
            response = await asyncio.to_thread(self._load_image, img_path)
            self.image = await asyncio.to_thread(self._get_image_name, response)
            logging.info(f"Getting image name: {self.image}")


            template_host_path = self.template_path
            feedback_host_path = self.feedback_path

            os.chmod(template_host_path, 0o777)
            os.chmod(feedback_host_path, 0o777)

            template_container_path = "/home/jovyan/task.ipynb"
            feedback_container_path =  "/home/jovyan/feedback.md"
            self.volumes = {template_host_path: {"bind": template_container_path, "mode": "rw"}, 
                            feedback_host_path: {"bind":feedback_container_path, "mode":"rw"}}
            os.remove(img_path)
            return await super().start()
        except Exception as e:
            logging.error(f"Error during start: {e}")
            raise e

    def _clear(self):
        if self.template_path and os.path.exists(self.template_path):
            os.remove(self.template_path)
        if self.feedback_path and os.path.exists (self.feedback_path):
            os.remove(self.feedback_path)
        
    def _save_progress(self):
        self._save_feedback_progess()
        self._save_template_progress()

    def _save_feedback_progess(self):
        # Need since during poll corresponding field could be bot set up
        if not self.feedback_path:
            logging.info("Noting to save - feedback_path is empty")
            return
        bucket = f"progress-{self.user.id}-{self.case_id}"
        key = "feedback"
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            client.fput_object(bucket, key, self.feedback_path)
            logging.info("Feedback was saved!")
        except Exception as e:
            logging.info(f"Failed to save feedback: {e}")
        # finally:
        #     if os.path.exists(self.feedback_path):
        #         os.remove(self.feedback_path)

    def _save_template_progress(self):
        if not self.template_path:
            logging.info("Nothing to save — template_path is None")
            return
        bucket = f"progress-{self.user.id}-{self.case_id}"
        key = "template"
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            client.fput_object(bucket, key, self.template_path)
            logging.info("Progress was saved!")
        except Exception as e:
            logging.error(f"Failed to save progress: {e}")
        # finally:
            # if os.path.exists(self.template_path):
            #     os.remove(self.template_path)

    async def stop(self, now=False):
        try:
            await asyncio.to_thread(self._save_progress)
        except Exception as e:
            logging.error(f"Error saving progress: {e}")
        finally:
            self._clear() # async?
            return await super().stop(now)

    async def poll(self):
        try:
            await asyncio.to_thread(self._save_progress)
        except Exception as e:
            logging.error(f"Error saving progress: {e}")
        finally:
            return await super().poll()

    async def _get_case_id(self) -> str:
        auth = self.auth_state
        if not auth:
            logging.error("No authentication state found for user.")
            raise RuntimeError("No authentication state found for user.")
        case_id = auth.get("case_id")
        if not case_id:
            logging.error("No case_id found in authentication state.")
            raise RuntimeError("No case_id found in authentication state.")
        logging.info(f"Case ID retrieved: {case_id}")
        return case_id

    def _load_image(self, img_path: str):
        """
        Загружает Docker-образ из тар-файла и возвращает список
        Docker-питоновских Image-объектов.
        """
        client = docker.from_env()
        with open(img_path, "rb") as f:
            images = client.images.load(f.read())
        logging.info(
            f"Tarball {img_path} загружен в Docker, получено образов: {len(images)}"
        )
        return images

    def _get_image_name(self, images) -> str:
        """
        Берёт первый объект Image и пытается вернуть его тег.
        """
        if not images:
            raise RuntimeError("Загрузка образа вернула пустой список")
        img = images[0]
        tags = img.tags  # список строк вида "myrepo/myimage:tag"
        if not tags:
            raise RuntimeError("У загруженного образа нет ни одного тега")
        return tags[0]

    def _get_image(self, case_id: str):
        img_path = f"/tmp/img_{self.user.id}_{case_id}.tar"
        img_path = self._get_data_from_db(f"case-{case_id}", "image", img_path)
        return img_path


    def _get_feedback(self, case_id):

        feedback_path = f"/tmp/feedback_{self.user.id}_{case_id}"
        if client.bucket_exists(f"progress-{self.user.id}-{case_id}"):
            try:
                feedback_path = self._get_data_from_db(
                    f"progress-{self.user.id}-{case_id}", "feedback", feedback_path
                )
                logging.info("Fetched saved feedback!")
            except Exception as e:
                logging.info("No saved feedback in DB!")
                logging.info("Creating base feedback file")
                with open (feedback_path, 'w') as f:
                    f.write("""
                    Your feedback is empty. Push button to generate it !
                    """)
                return feedback_path
        else:

            logging.info("Creating base feedback file")
            with open (feedback_path, 'w') as f:
                f.write("""
                Your feedback is empty. Push button to generate it !
                """)
        return feedback_path

    def _get_template(self, case_id):
        template_path = f"/tmp/template_{self.user.id}_{case_id}.ipynb"
        if client.bucket_exists(f"progress-{self.user.id}-{case_id}"):
            try:

                template_path = self._get_data_from_db(
                    f"progress-{self.user.id}-{case_id}", "template", template_path
                )
                logging.info("Fetched saved template progress!")
            except Exception as e:
                logging.info("No saved progess in BD!")
                return self._get_data_from_db(
                    f"case-{case_id}", "template", template_path
                )

        else:
            template_path = self._get_data_from_db(
                f"case-{case_id}", "template", template_path
            )
        return template_path

    def _get_data_from_db(self, bucket, key, file_to_save) -> str:
        logging.info("Starting fetching data from DB...")
        response = client.get_object(f"{bucket}", f"{key}")
        logging.info("Finished fetching data!")
        try:
            with open(file_to_save, "wb") as img:
                for chunk in response.stream(32 * 1024):
                    img.write(chunk)
        finally:
            response.close()
            response.release_conn()
        return file_to_save

"""
Custom Docker Spawner for JupyterHub.

This module provides a custom Docker spawner that extends the base DockerSpawner
to manage case-specific environments for users. It handles fetching Docker images,
templates, and other case data from a MinIO storage backend, and manages
saving user progress.
"""
import os
import subprocess
import logging
import sys
import asyncio
import re
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error
from dockerspawner import DockerSpawner

load_dotenv()

# MinIO connection setup from environment variables
HOST = os.getenv("HOST_IP")
MINIO_PORT = os.getenv("MINIO_PORT_EXTERNAL")

ENDPOINT = f"{HOST}:{MINIO_PORT}"
ACCESS_KEY = os.getenv("MINIO_ROOT_USER")
SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD")
MINIO_CLIENT = Minio(ENDPOINT, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=False)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)


class CustomDockerSpawner(DockerSpawner):
    """
    A custom Docker spawner for JupyterHub that manages case-specific environments.

    This spawner extends DockerSpawner to provide functionality for:
    - Loading case-specific Docker images from a MinIO storage backend.
    - Managing template notebooks and feedback files for each case.
    - Saving and restoring user progress across sessions.
    - Mounting case files as volumes into the user's container.

    Attributes:
        template_path (str): The local filesystem path to the template notebook file.
        feedback_path (str): The local filesystem path to the feedback file.
        case_id (str): The identifier for the current case being used.
    """

    template_path = None
    feedback_path = None
    case_id = None

    async def start(self):
        """
        Starts the Docker container with a case-specific configuration.

        This method orchestrates the setup of the user's environment by:
        1. Retrieving the `case_id` from user options.
        2. Downloading the case-specific Docker image, template notebook, and feedback
           file from the MinIO backend.
        3. Loading the Docker image into the local Docker daemon.
        4. Configuring volume mounts to make the template and feedback files
           available inside the container.
        5. Calling the parent class's start method to launch the container.

        Returns:
            The result of the parent `start()` method, typically the container's
            IP address and port.

        Raises:
            Exception: If any step in the setup process fails.
        """
        img_path: str | None = None
        try:
            # Get case_id from user options, default to "1" if not provided.
            self.case_id = self.user_options.get("case_id")
            if self.case_id:
                logging.info("Got case ID: %s", self.case_id)
            else:
                self.case_id = "1"
                logging.info("No case ID provided. Setting to default: 1")

            # Download assets from MinIO
            logging.info("Getting image from DB for case ID: %s", self.case_id)
            img_path = await asyncio.to_thread(self._get_image, self.case_id)
            logging.info("Image path: %s", img_path)

            logging.info("Getting template for case ID: %s", self.case_id)
            self.template_path = await asyncio.to_thread(self._get_template, self.case_id)
            logging.info("Template path: %s", self.template_path)

            logging.info("Getting feedback for case ID: %s", self.case_id)
            self.feedback_path = await asyncio.to_thread(self._get_feedback, self.case_id)
            logging.info("Feedback path: %s", self.feedback_path)

            # Load the downloaded image into the local Docker daemon
            logging.info("Loading image to local docker repository: %s", img_path)
            self.image = await asyncio.to_thread(self._load_image, img_path)
            logging.info("Loaded image name: %s", self.image)

            # Set up paths and permissions for volume mounting
            template_host_path = self.template_path
            feedback_host_path = self.feedback_path

            os.chmod(template_host_path, 0o777)
            os.chmod(feedback_host_path, 0o777)

            # Configure volume mounts
            template_container_path = "/home/jovyan/template.ipynb"
            feedback_container_path = "/home/jovyan/feedback.md"
            self.volumes = {
                template_host_path: {"bind": template_container_path, "mode": "rw"},
                feedback_host_path: {"bind": feedback_container_path, "mode": "rw"},
            }

            # Clean up the temporary image file and start the container
            if img_path:
                os.remove(img_path)
            return await super().start()
        except Exception as e:
            logging.error("Error during start: %s", e)
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
            raise

    def _clear(self):
        """
        Cleans up temporary files created during the spawner's session.

        This method removes the downloaded template and feedback files from the
        local filesystem to avoid clutter.
        """
        if self.template_path and os.path.exists(self.template_path):
            os.remove(self.template_path)
        if self.feedback_path and os.path.exists(self.feedback_path):
            os.remove(self.feedback_path)

    def _save_progress(self):
        """
        Saves the user's current progress to the MinIO backend.

        This method orchestrates the saving of both the feedback file and the
        template notebook.
        """
        self._save_feedback_progess()
        self._save_template_progress()

    def _save_feedback_progess(self):
        """
        Saves the current state of the feedback file to MinIO.

        It creates a user-specific bucket if one does not exist and uploads
        the feedback file to it.
        """
        if not self.feedback_path:
            logging.info("Nothing to save - feedback_path is empty")
            return

        bucket = f"progress-{self.user.id}-{self.case_id}"
        key = "feedback.md"
        try:
            if not MINIO_CLIENT.bucket_exists(bucket):
                MINIO_CLIENT.make_bucket(bucket)
            MINIO_CLIENT.fput_object(bucket, key, self.feedback_path)
            logging.info("Feedback was saved!")
        except S3Error as e:
            logging.info("Failed to save feedback: %s", e)

    def _save_template_progress(self):
        """
        Saves the current state of the template notebook to MinIO.

        It creates a user-specific bucket if one does not exist and uploads
        the notebook file to it.
        """
        if not self.template_path:
            logging.info("Nothing to save — template_path is None")
            return

        bucket = f"progress-{self.user.id}-{self.case_id}"
        key = "template.ipynb"
        try:
            if not MINIO_CLIENT.bucket_exists(bucket):
                MINIO_CLIENT.make_bucket(bucket)
            MINIO_CLIENT.fput_object(bucket, key, self.template_path)
            logging.info("Progress was saved!")
        except S3Error as e:
            logging.error("Failed to save progress: %s", e)

    async def stop(self, now=False):
        """
        Stops the container, saving user progress before shutdown.

        Args:
            now (bool): If True, forces an immediate stop without cleanup.

        Returns:
            The result of the parent `stop()` method.
        """
        try:
            await asyncio.to_thread(self._save_progress)
        except S3Error as e:
            logging.error("Error saving progress to MinIO: %s", e)

        self._clear()
        return await super().stop(now)

    async def poll(self):
        """
        Polls the container's status and saves progress periodically.

        JupyterHub calls this method to check if the container is still running.
        This implementation uses the hook to save user progress.

        Returns:
            The result of the parent `poll()` method (None if running, exit code otherwise).
        """
        status = await super().poll()
        try:
            # Save progress only if the container is still running
            if status is None:
                await asyncio.to_thread(self._save_progress)
        except S3Error as e:
            logging.error("Error saving progress to MinIO during poll: %s", e)
        return status

    async def _get_case_id(self) -> str:
        """
        Retrieves the case_id from the user's authentication state.

        Returns:
            The case identifier string.

        Raises:
            RuntimeError: If the authentication state or case_id is not found.
        """
        auth_state = await self.user.get_auth_state()
        if not auth_state:
            logging.error("No authentication state found for user.")
            raise RuntimeError("No authentication state found for user.")
        case_id = auth_state.get("case_id")
        if not case_id:
            logging.error("No case_id found in authentication state.")
            raise RuntimeError("No case_id found in authentication state.")
        logging.info("Case ID retrieved: %s", case_id)
        return case_id

    def _load_image(self, img_path: str) -> str:
        """
        Loads a Docker image from a .tar file into the local Docker daemon.

        Args:
            img_path: The local filesystem path to the image .tar file.

        Returns:
            The name of the loaded Docker image (e.g., 'my-image:latest').

        Raises:
            RuntimeError: If the image name cannot be parsed from the `docker load` output.
            subprocess.CalledProcessError: If the `docker load` command fails.
        """
        try:
            output = subprocess.check_output(
                ["docker", "load", "-i", img_path],
                stderr=subprocess.STDOUT,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logging.error("Could not load image to local repository: %s", e.output)
            raise

        match = re.search(r"Loaded image:\s+(.+)", output)
        if match:
            image_name = match.group(1).strip()
            return image_name
        raise RuntimeError(f"Could not parse docker image name from output: {output}")

    def _get_image_name(self, images) -> str:
        """
        Extracts the tag from the first image in a list of Docker images.

        Args:
            images: A list of Docker image objects.

        Returns:
            The first tag of the first image in the list.

        Raises:
            RuntimeError: If the list is empty or the image has no tags.
        """
        if not images:
            raise RuntimeError("Image loading returned an empty list.")
        img = images[0]
        tags = img.tags
        if not tags:
            raise RuntimeError("Loaded image has no tags.")
        return tags[0]

    def _get_image(self, case_id: str) -> str:
        """
        Retrieves the Docker image for a specific case from MinIO.

        Args:
            case_id: The identifier for the case.

        Returns:
            The local filesystem path to the downloaded image .tar file.
        """
        img_path = f"/tmp/img_{self.user.id}_{case_id}.tar"
        img_path = self._get_data_from_db(f"case-{case_id}", "image.tar", img_path)
        return img_path

    def _get_feedback(self, case_id: str) -> str:
        """
        Retrieves the feedback file for a specific case.

        It first attempts to load saved progress for the user. If no progress
        is found, it creates a default, empty feedback file.

        Args:
            case_id: The identifier for the case.

        Returns:
            The local filesystem path to the feedback file.
        """
        feedback_path = f"/tmp/feedback_{self.user.id}_{case_id}"

        # Check if a progress bucket exists for this user and case
        if MINIO_CLIENT.bucket_exists(f"progress-{self.user.id}-{case_id}"):
            try:
                # Attempt to download the saved feedback file
                feedback_path = self._get_data_from_db(
                    f"progress-{self.user.id}-{case_id}", "feedback.md", feedback_path
                )
                logging.info("Fetched saved feedback!")
                return feedback_path
            except S3Error:
                # If download fails, create a base file
                logging.info("No saved feedback in DB! Creating base feedback file")
                with open(feedback_path, "w", encoding="utf-8") as f:
                    f.write("Your feedback is empty. Push button to generate it !")
                return feedback_path

        # If no progress bucket exists, create a base file
        logging.info("Creating base feedback file")
        with open(feedback_path, "w", encoding="utf-8") as f:
            f.write("Your feedback is empty. Push button to generate it !")
        return feedback_path

    def _get_template(self, case_id: str) -> str:
        """
        Retrieves the template notebook for a specific case.

        It first attempts to load a saved version of the user's notebook.
        If no saved progress is found, it falls back to loading the original,
        default template for the case.

        Args:
            case_id: The identifier for the case.

        Returns:
            The local filesystem path to the template notebook file.
        """
        template_path = f"/tmp/template_{self.user.id}_{case_id}.ipynb"

        # Check if a progress bucket exists for this user and case
        if MINIO_CLIENT.bucket_exists(f"progress-{self.user.id}-{case_id}"):
            try:
                # Attempt to download the saved notebook
                template_path = self._get_data_from_db(
                    f"progress-{self.user.id}-{case_id}",
                    "template.ipynb",
                    template_path,
                )
                logging.info("Fetched saved template progress!")
            except S3Error:
                # If download fails, fetch the original template
                logging.info("No saved progess in DB!")
                return self._get_data_from_db(
                    f"case-{case_id}", "template.ipynb", template_path
                )
        else:
            # If no progress bucket exists, fetch the original template
            template_path = self._get_data_from_db(
                f"case-{case_id}", "template.ipynb", template_path
            )
        return template_path

    def _get_data_from_db(self, bucket: str, key: str, file_to_save: str) -> str:
        """
        A generic helper to download a file from a MinIO bucket.

        Args:
            bucket: The name of the MinIO bucket.
            key: The object key (filename) within the bucket.
            file_to_save: The local path where the downloaded file should be saved.

        Returns:
            The local path where the file was saved (`file_to_save`).
        """
        logging.info("Starting fetching data from DB...")
        response = None
        try:
            response = MINIO_CLIENT.get_object(bucket, key)
            logging.info("Finished fetching data!")
            with open(file_to_save, "wb") as f:
                for chunk in response.stream(32 * 1024):
                    f.write(chunk)
        finally:
            if response:
                response.close()
                response.release_conn()
        return file_to_save

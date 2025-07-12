import tempfile
import subprocess
import uuid
import os
import logging
import asyncpg
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from profile_uploader import ProfileUploader
from validation import FileValidator

logger = logging.getLogger(__name__)


class CaseUploader:
    def __init__(self, conn: asyncpg.Connection, minio_client: Minio, case_uploader: ProfileUploader, validator: FileValidator):
        self._conn = conn
        self._minio_client = minio_client
        self._case_uploader = case_uploader
        self._validator = validator

    async def upload_case(
        self,
        case_name: str,
        requirements: UploadFile,
        dataset: UploadFile,
        profile: UploadFile,
        template: UploadFile,
    ):
        """
        Handles the upload of a case: builds Docker image, saves image to MinIO, records in DB.
        """
        case_id = str(uuid.uuid4())
        logger.debug(f"Starting upload for case_id: {case_id}")
        
        # Validate file extensions early
        self._validator.validate_file_extensions(requirements, dataset, profile, template)
        
        # Validate and cache profile content early
        validated_profile_content = await self._validator.validate_and_cache_profile(profile)
        
        # Ensure MinIO bucket exists
        await self.ensure_minio_bucket_exists()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save files for repo2docker
            req_path = f"{tmpdir}/requirements.txt"
            data_path = f"{tmpdir}/dataset"
            prof_path = f"{tmpdir}/profile.ipynb"
            tmpl_path = f"{tmpdir}/template.ipynb"

            logger.debug("Saving uploaded files...")
            await self._save_file(requirements, req_path)
            await self._save_file(dataset, data_path)
            await self._save_file(validated_profile_content, prof_path)
            await self._save_file(template, tmpl_path)
            logger.debug("Files saved successfully")

            # Build Docker image with repo2docker
            image_tag = f"case-{case_id}"
            logger.debug(f"Building Docker image with tag: {image_tag}")
            await self._build_docker_image_with_repo2docker(tmpdir, image_tag)
            logger.debug("Docker image built successfully")

            # Save Docker image to tar file and upload to MinIO
            logger.debug("Saving and uploading Docker image to MinIO...")
            docker_image_url = await self._save_and_upload_docker_image(image_tag, case_id)
            logger.debug(f"Docker image uploaded to MinIO: {docker_image_url}")
            
            # Upload profile to MinIO
            logger.debug("Uploading profile to MinIO...")
            profile_url = await self._upload_file_to_minio(prof_path, f"profiles/{case_id}.ipynb")
            logger.debug(f"Profile uploaded to MinIO: {profile_url}")

            # Insert case record into database
            logger.debug("Inserting case record into database...")
            await self._insert_case_record(case_id, case_name, profile_url, docker_image_url)
            logger.debug("Case record inserted successfully")
            
            # Parse and store profile structure in database
            logger.debug("Parsing and storing profile structure...")
            await self._case_uploader.store_profile(validated_profile_content, case_id)
            logger.debug("Profile structure stored successfully")

            logger.debug(f"Upload completed successfully for case_id: {case_id}")
    ***REMOVED*** case_id

    async def _save_file(self, file_data: UploadFile | bytes, dest_path: str):
        """Save file data to temporary directory.
        
        Args:
            file_data: Either an UploadFile or raw bytes content
            dest_path: Destination file path
        """
        with open(dest_path, "wb") as out_file:
            if isinstance(file_data, bytes):
                out_file.write(file_data)
            else:
                content = await file_data.read()
                out_file.write(content)

    async def _build_docker_image_with_repo2docker(self, build_dir: str, image_tag: str):
        """Build Docker image using repo2docker and stream output to logs."""
        cmd = [
            "jupyter-repo2docker",
            "--no-run",
            "--user-name", "jovyan", # jupyter-repo2docker does not allow run by root
            "--user-id", "1000",
            "--image-name", image_tag,
            build_dir,
        ]
        logger.debug(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        # Stream output line by line
        if process.stdout is not None:
            for line in process.stdout:
                logger.debug(line.rstrip())
            process.stdout.close()
        else:
            logger.warning("No output from process.")

        process.wait()
        if process.returncode != 0:
            logger.error("Failed to build Docker image, see logs above.")
            raise RuntimeError(f"Failed to build Docker image, see logs above.")

    async def _save_and_upload_docker_image(self, image_tag: str, case_id: str) -> str:
        """Save Docker image to tar file and upload to MinIO."""
        try:
            # Save Docker image to tar file using CLI
            tar_path = f"/tmp/{case_id}.tar"
            logger.debug(f"Saving Docker image {image_tag} to {tar_path}...")
            cmd = ["docker", "save", "-o", tar_path, image_tag]
            
            result = subprocess.run(cmd, text=True, capture_output=True)
            if result.returncode != 0:
                logger.error(f"Docker save failed: {result.stderr}")
                raise RuntimeError(f"Failed to save Docker image: {result.stderr}")
            logger.debug(f"Docker image saved to {tar_path}")
            
            # Upload tar file to MinIO
            minio_path = f"docker-images/{case_id}.tar"
            logger.debug(f"Uploading {tar_path} to MinIO at {minio_path}...")
            self._minio_client.fput_object("cases", minio_path, tar_path)
            logger.debug(f"Successfully uploaded to MinIO: {minio_path}")
            
            # Clean up local tar file
            os.unlink(tar_path)
            logger.debug(f"Cleaned up local file: {tar_path}")
            
    ***REMOVED*** minio_path
                
        except Exception as e:
            logger.error(f"Error in _save_and_upload_docker_image: {e}")
            raise RuntimeError(f"Failed to save and upload Docker image: {e}")

    async def _upload_file_to_minio(self, file_path: str, minio_path: str) -> str:
        """Upload file to MinIO."""
        try:
            logger.debug(f"Uploading {file_path} to MinIO at {minio_path}...")
            self._minio_client.fput_object(
                "cases", minio_path, file_path
            )
            logger.debug(f"Successfully uploaded to MinIO: {minio_path}")
    ***REMOVED*** minio_path
        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            raise RuntimeError(f"Failed to upload file to MinIO: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in _upload_file_to_minio: {e}")
            raise RuntimeError(f"Failed to upload file to MinIO: {e}")

    async def _insert_case_record(self, case_id: str, case_name: str, profile_url: str, docker_image_url: str):
        """Insert case record into database."""
        try:
            logger.debug(f"Inserting case record: id={case_id}, name={case_name}")
            await self._conn.execute(
                """
                INSERT INTO cases(id, name, profile_url, docker_image_url, created_at)
                VALUES($1, $2, $3, $4, now())
                """,
                case_id, case_name, profile_url, docker_image_url
            )
            logger.debug(f"Successfully inserted case record for {case_id}")
        except Exception as e:
            logger.error(f"Database insertion error: {e}")
            raise RuntimeError(f"Failed to insert case record: {e}")

    async def ensure_minio_bucket_exists(self):
        """Ensure the MinIO bucket exists."""
        try:
            if not self._minio_client.bucket_exists("cases"):
                self._minio_client.make_bucket("cases")
        except S3Error as e:
            raise RuntimeError(f"Failed to create MinIO bucket: {e}")
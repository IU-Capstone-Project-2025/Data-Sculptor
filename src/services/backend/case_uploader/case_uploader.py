import tempfile
import subprocess
import uuid
import os
import logging
import asyncpg
from pathlib import Path
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from profile_uploader import ProfileUploader
from validation import FileValidator

logger = logging.getLogger(__name__)


class CaseUploader:
    def __init__(
        self,
        conn: asyncpg.Connection,
        minio_client: Minio,
        case_uploader: ProfileUploader,
        validator: FileValidator,
    ):
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
        Handles the upload of a case: builds Docker image with environment from requirements,
        includes dataset in container, saves everything to case-specific MinIO bucket, records in DB.
        """
        case_id = str(uuid.uuid4())
        logger.info(f"Starting upload for case_id: {case_id}")

        # Validate file extensions early
        self._validator.validate_file_extensions(
            requirements, dataset, profile, template
        )

        # Validate and cache profile content early
        validated_profile_content = await self._validator.validate_and_cache_profile(
            profile
        )

        # Ensure MinIO bucket exists
        await self.ensure_minio_bucket_exists()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create case-specific directory structure
            case_dir = f"{tmpdir}/case-{case_id}"
            os.makedirs(case_dir, exist_ok=True)

            # Save requirements.txt for repo2docker to install environment
            req_path = f"{case_dir}/requirements.txt"
            # Preserve dataset file extension
            dataset_ext = Path(dataset.filename).suffix if dataset.filename else ""
            data_path = f"{case_dir}/dataset{dataset_ext}"
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
            await self._build_docker_image_with_repo2docker(case_dir, image_tag)
            logger.debug("Docker image built successfully")

            # Create case-specific MinIO bucket
            bucket_name = f"case-{case_id}"
            logger.debug(f"Creating MinIO bucket: {bucket_name}")
            await self._ensure_case_bucket_exists(bucket_name)

            # Save Docker image to tar file and upload to case bucket
            logger.debug("Saving and uploading Docker image to case bucket...")
            docker_image_path = await self._save_and_upload_docker_image(
                image_tag, case_id, bucket_name
            )
            logger.info(f"Docker image uploaded to case bucket: {docker_image_path}")

            # Upload template and profile to case bucket
            logger.debug("Uploading template and profile to case bucket...")
            await self._upload_file_to_case_bucket(
                tmpl_path, f"template.ipynb", bucket_name
            )
            await self._upload_file_to_case_bucket(
                prof_path, f"profile.ipynb", bucket_name
            )
            logger.debug("Template and profile uploaded to case bucket")

            # Insert case record into database with bucket URL
            logger.debug("Inserting case record into database...")
            bucket_url = f"minio://{bucket_name}"
            await self._insert_case_record(case_id, case_name, bucket_url)
            logger.info("Case record inserted successfully")
            
            logger.debug("Parsing and storing profile structure...")
            await self._case_uploader.store_profile(validated_profile_content, case_id)
            logger.info("Profile structure stored successfully")

            logger.info(f"Upload completed successfully for case_id: {case_id}")
            return case_id

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

    async def _build_docker_image_with_repo2docker(
        self, build_dir: str, image_tag: str
    ):
        """Build Docker image using repo2docker and stream output to logs."""
        cmd = [
            "jupyter-repo2docker",
            "--no-run",
            "--user-name",
            "jovyan",  # jupyter-repo2docker does not allow run by root
            "--user-id",
            "1000",
            "--image-name",
            image_tag,
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

        # Remove requirements.txt from the built image
        logger.debug(f"Removing requirements.txt from image {image_tag}...")
        await self._remove_requirements_from_image(image_tag)
        logger.debug("requirements.txt removed from image successfully")

    async def _remove_requirements_from_image(self, image_tag: str):
        """Remove requirements.txt from the built Docker image."""
        container_name = f"temp-{image_tag}-{uuid.uuid4().hex[:8]}"
        
        try:
            # Run a temporary container in detached mode with sleep to keep it running
            run_cmd = ["docker", "run", "-d", "--name", container_name, image_tag, "sleep", "infinity"]
            result = subprocess.run(run_cmd, text=True, capture_output=True)
            if result.returncode != 0:
                logger.error(f"Failed to create temporary container: {result.stderr}")
                raise RuntimeError(f"Failed to create temporary container: {result.stderr}")
            
            # Try to remove requirements.txt from common locations
            possible_paths = [
                "/home/jovyan/requirements.txt",
                "/app/requirements.txt", 
                "/workspace/requirements.txt",
                "/home/jovyan/work/requirements.txt"
            ]
            
            removed = False
            for path in possible_paths:
                exec_cmd = ["docker", "exec", container_name, "test", "-f", path]
                result = subprocess.run(exec_cmd, text=True, capture_output=True)
                if result.returncode == 0:
                    # File exists, remove it
                    rm_cmd = ["docker", "exec", container_name, "rm", "-f", path]
                    result = subprocess.run(rm_cmd, text=True, capture_output=True)
                    if result.returncode == 0:
                        logger.debug(f"Removed requirements.txt from {path}")
                        removed = True
                    else:
                        logger.warning(f"Failed to remove {path}: {result.stderr}")
            
            if not removed:
                logger.warning("requirements.txt not found in common locations")
            
            # Commit the changes to create a new image
            commit_cmd = ["docker", "commit", container_name, image_tag]
            result = subprocess.run(commit_cmd, text=True, capture_output=True)
            if result.returncode != 0:
                logger.error(f"Failed to commit changes: {result.stderr}")
                raise RuntimeError(f"Failed to commit changes: {result.stderr}")
            
            logger.debug(f"Successfully processed image {image_tag}")
            
        except Exception as e:
            logger.error(f"Error processing image {image_tag}: {e}")
            raise RuntimeError(f"Failed to process image: {e}")
        finally:
            # Always clean up the temporary container
            try:
                stop_cmd = ["docker", "stop", container_name]
                subprocess.run(stop_cmd, text=True, capture_output=True)
                rm_cmd = ["docker", "rm", container_name]
                subprocess.run(rm_cmd, text=True, capture_output=True)
                logger.debug(f"Cleaned up temporary container: {container_name}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up container {container_name}: {cleanup_error}")

    async def _save_and_upload_docker_image(
        self, image_tag: str, case_id: str, bucket_name: str
    ) -> str:
        """Save Docker image to tar file and upload to case-specific MinIO bucket."""
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

            # Upload tar file to case-specific bucket
            minio_path = f"image.tar"
            logger.debug(
                f"Uploading {tar_path} to case bucket {bucket_name} at {minio_path}..."
            )
            self._minio_client.fput_object(bucket_name, minio_path, tar_path)
            logger.debug(f"Successfully uploaded to case bucket: {minio_path}")

            # Clean up local tar file
            os.unlink(tar_path)
            logger.debug(f"Cleaned up local file: {tar_path}")

            return minio_path

        except Exception as e:
            logger.error(f"Error in _save_and_upload_docker_image: {e}")
            raise RuntimeError(f"Failed to save and upload Docker image: {e}")

    async def _upload_file_to_case_bucket(
        self, file_path: str, minio_path: str, bucket_name: str
    ) -> str:
        """Upload file to case-specific MinIO bucket."""
        try:
            logger.debug(
                f"Uploading {file_path} to case bucket {bucket_name} at {minio_path}..."
            )
            self._minio_client.fput_object(bucket_name, minio_path, file_path)
            logger.debug(f"Successfully uploaded to case bucket: {minio_path}")
            return minio_path
        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            raise RuntimeError(f"Failed to upload file to case bucket: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in _upload_file_to_case_bucket: {e}")
            raise RuntimeError(f"Failed to upload file to case bucket: {e}")

    async def _insert_case_record(self, case_id: str, case_name: str, bucket_url: str):
        """Insert case record into database with bucket URL."""
        try:
            logger.debug(
                f"Inserting case record: id={case_id}, name={case_name}, bucket={bucket_url}"
            )
            await self._conn.execute(
                """
                    INSERT INTO cases(id, name, bucket_url, created_at)
                    VALUES($1, $2, $3, now())
                    """,
                case_id,
                case_name,
                bucket_url,
            )
            logger.debug(f"Successfully inserted case record for {case_id}")
        except Exception as e:
            logger.error(f"Database insertion error: {e}")
            raise RuntimeError(f"Failed to insert case record: {e}")

    async def _ensure_case_bucket_exists(self, bucket_name: str):
        """Ensure the case-specific MinIO bucket exists."""
        try:
            if not self._minio_client.bucket_exists(bucket_name):
                self._minio_client.make_bucket(bucket_name)
                logger.debug(f"Created case bucket: {bucket_name}")
            else:
                logger.debug(f"Case bucket already exists: {bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to create case bucket {bucket_name}: {e}")
            raise RuntimeError(f"Failed to create case bucket {bucket_name}: {e}")

    async def ensure_minio_bucket_exists(self):
        """Ensure the main cases bucket exists (for backward compatibility)."""
        try:
            if not self._minio_client.bucket_exists("cases"):
                self._minio_client.make_bucket("cases")
        except S3Error as e:
            logger.error(f"Failed to create MinIO bucket: {e}")
            raise RuntimeError(f"Failed to create MinIO bucket: {e}")

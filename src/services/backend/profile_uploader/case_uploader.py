import tempfile
import subprocess
import uuid
import os
from pathlib import Path
import asyncpg
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error


class CaseUploader:
    def __init__(self, pg_pool: asyncpg.Pool, minio_client: Minio):
        self._pg_pool = pg_pool
        self._minio_client = minio_client

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
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save files for repo2docker
            req_path = f"{tmpdir}/requirements.txt"
            data_path = f"{tmpdir}/dataset"
            prof_path = f"{tmpdir}/profile.ipynb"
            tmpl_path = f"{tmpdir}/template.ipynb"

            await self._save_upload_file(requirements, req_path)
            await self._save_upload_file(dataset, data_path)
            await self._save_upload_file(profile, prof_path)
            await self._save_upload_file(template, tmpl_path)

            # Build Docker image with repo2docker
            image_tag = f"case-{case_id}"
            await self._build_docker_image_with_repo2docker(tmpdir, image_tag)

            # Save Docker image to tar file and upload to MinIO
            docker_image_url = await self._save_and_upload_docker_image(image_tag, case_id)
            
            # Upload profile to MinIO
            profile_url = await self._upload_file_to_minio(prof_path, f"profiles/{case_id}.ipynb")

            # Insert case record into database
            await self._insert_case_record(case_id, case_name, profile_url, docker_image_url)

    ***REMOVED*** case_id

    async def _save_upload_file(self, upload_file: UploadFile, dest_path: str):
        """Save uploaded file to temporary directory."""
        with open(dest_path, "wb") as out_file:
            content = await upload_file.read()
            out_file.write(content)

    async def _build_docker_image_with_repo2docker(self, build_dir: str, image_tag: str):
        """Build Docker image using repo2docker."""
        cmd = [
            "jupyter-repo2docker",
            "--no-run",
            "--user-name", "jovyan",
            "--user-id", "1000",
            "--image-name", image_tag,
            build_dir,
        ]
        
        result = subprocess.run(cmd, text=True, capture_output=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to build Docker image: {result.stderr}")

    async def _save_and_upload_docker_image(self, image_tag: str, case_id: str) -> str:
        """Save Docker image to tar file and upload to MinIO."""
        try:
            # Save Docker image to tar file using CLI
            tar_path = f"/tmp/{case_id}.tar"
            cmd = ["docker", "save", "-o", tar_path, image_tag]
            
            result = subprocess.run(cmd, text=True, capture_output=True)
            if result.returncode != 0:
                raise RuntimeError(f"Failed to save Docker image: {result.stderr}")
            
            # Upload tar file to MinIO
            minio_path = f"docker-images/{case_id}.tar"
            self._minio_client.fput_object("cases", minio_path, tar_path)
            
            # Clean up local tar file
            os.unlink(tar_path)
            
    ***REMOVED*** minio_path
                
        except Exception as e:
            raise RuntimeError(f"Failed to save and upload Docker image: {e}")

    async def _upload_file_to_minio(self, file_path: str, minio_path: str) -> str:
        """Upload file to MinIO."""
        try:
            self._minio_client.fput_object(
                "cases", minio_path, file_path
            )
    ***REMOVED*** minio_path
        except S3Error as e:
            raise RuntimeError(f"Failed to upload file to MinIO: {e}")

    async def _insert_case_record(self, case_id: str, case_name: str, profile_url: str, docker_image_url: str):
        """Insert case record into database."""
        async with self._pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO cases(id, name, profile_url, docker_image_url, created_at)
                VALUES($1, $2, $3, $4, now())
                """,
                case_id, case_name, profile_url, docker_image_url
            )

    async def ensure_minio_bucket_exists(self):
        """Ensure the MinIO bucket exists."""
        try:
            if not self._minio_client.bucket_exists("cases"):
                self._minio_client.make_bucket("cases")
        except S3Error as e:
            raise RuntimeError(f"Failed to create MinIO bucket: {e}")
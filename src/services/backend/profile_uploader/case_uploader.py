import tempfile
import subprocess
import uuid
import os
from pathlib import Path
import asyncpg
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error
import sys


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
        Handles the upload of a case: builds Docker image with environment from requirements,
        includes dataset in container, saves everything to case-specific MinIO bucket, records in DB.
        """
        case_id = str(uuid.uuid4())
        print(f"Starting upload for case_id: {case_id}")
        
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

            print("Saving uploaded files...")
            await self._save_upload_file(requirements, req_path)
            await self._save_upload_file(dataset, data_path)
            await self._save_upload_file(profile, prof_path)
            await self._save_upload_file(template, tmpl_path)
            print("Files saved successfully")

            # Build Docker image with repo2docker
            image_tag = f"case-{case_id}"
            print(f"Building Docker image with tag: {image_tag}")
            await self._build_docker_image_with_repo2docker(case_dir, image_tag)
            print("Docker image built successfully")

            # Create case-specific MinIO bucket
            bucket_name = f"case-{case_id}"
            print(f"Creating MinIO bucket: {bucket_name}")
            await self._ensure_case_bucket_exists(bucket_name)

            # Save Docker image to tar file and upload to case bucket
            print("Saving and uploading Docker image to case bucket...")
            docker_image_path = await self._save_and_upload_docker_image(image_tag, case_id, bucket_name)
            print(f"Docker image uploaded to case bucket: {docker_image_path}")
            
            # Upload template and profile to case bucket
            print("Uploading template and profile to case bucket...")
            template_path = await self._upload_file_to_case_bucket(tmpl_path, f"template.ipynb", bucket_name)
            profile_path = await self._upload_file_to_case_bucket(prof_path, f"profile.ipynb", bucket_name)
            print(f"Template and profile uploaded to case bucket")

            # Insert case record into database with bucket URL
            print("Inserting case record into database...")
            bucket_url = f"minio://{bucket_name}"
            await self._insert_case_record(case_id, case_name, bucket_url)
            print("Case record inserted successfully")

            print(f"Upload completed successfully for case_id: {case_id}")
            return case_id

    async def _save_upload_file(self, upload_file: UploadFile, dest_path: str):
        """Save uploaded file to temporary directory."""
        with open(dest_path, "wb") as out_file:
            content = await upload_file.read()
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
        print(f"Running command: {' '.join(cmd)}")
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
                print(line, end='')  # Already includes newline
            process.stdout.close()
        else:
            print("No output from process.")

        process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"Failed to build Docker image, see logs above.")
        
        # Remove requirements.txt from the built image
        print(f"Removing requirements.txt from image {image_tag}...")
        await self._remove_requirements_from_image(image_tag)
        print("requirements.txt removed from image successfully")

    async def _remove_requirements_from_image(self, image_tag: str):
        """Remove requirements.txt from the built Docker image."""
        container_name = f"temp-{image_tag}-{uuid.uuid4().hex[:8]}"
        
        try:
            # Run a temporary container
            run_cmd = ["docker", "run", "--name", container_name, image_tag, "true"]
            result = subprocess.run(run_cmd, text=True, capture_output=True)
            if result.returncode != 0:
                print(f"Failed to create temporary container: {result.stderr}")
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
                        print(f"Removed requirements.txt from {path}")
                        removed = True
                    else:
                        print(f"Failed to remove {path}: {result.stderr}")
            
            if not removed:
                print("Warning: requirements.txt not found in common locations")
            
            # Commit the changes to create a new image
            commit_cmd = ["docker", "commit", container_name, image_tag]
            result = subprocess.run(commit_cmd, text=True, capture_output=True)
            if result.returncode != 0:
                print(f"Failed to commit changes: {result.stderr}")
                raise RuntimeError(f"Failed to commit changes: {result.stderr}")
            
            print(f"Successfully processed image {image_tag}")
            
        except Exception as e:
            print(f"Error processing image {image_tag}: {e}")
            raise RuntimeError(f"Failed to process image: {e}")
        finally:
            # Always clean up the temporary container
            try:
                rm_cmd = ["docker", "rm", "-f", container_name]
                subprocess.run(rm_cmd, text=True, capture_output=True)
                print(f"Cleaned up temporary container: {container_name}")
            except Exception as cleanup_error:
                print(f"Warning: Failed to clean up container {container_name}: {cleanup_error}")

    async def _save_and_upload_docker_image(self, image_tag: str, case_id: str, bucket_name: str) -> str:
        """Save Docker image to tar file and upload to case-specific MinIO bucket."""
        try:
            # Save Docker image to tar file using CLI
            tar_path = f"/tmp/{case_id}.tar"
            print(f"Saving Docker image {image_tag} to {tar_path}...")
            cmd = ["docker", "save", "-o", tar_path, image_tag]
            
            result = subprocess.run(cmd, text=True, capture_output=True)
            if result.returncode != 0:
                print(f"Docker save failed: {result.stderr}")
                raise RuntimeError(f"Failed to save Docker image: {result.stderr}")
            print(f"Docker image saved to {tar_path}")
            
            # Upload tar file to case-specific bucket
            minio_path = f"image.tar"
            print(f"Uploading {tar_path} to case bucket {bucket_name} at {minio_path}...")
            self._minio_client.fput_object(bucket_name, minio_path, tar_path)
            print(f"Successfully uploaded to case bucket: {minio_path}")
            
            # Clean up local tar file
            os.unlink(tar_path)
            print(f"Cleaned up local file: {tar_path}")
            
            return minio_path
                
        except Exception as e:
            print(f"Error in _save_and_upload_docker_image: {e}")
            raise RuntimeError(f"Failed to save and upload Docker image: {e}")

    async def _upload_file_to_case_bucket(self, file_path: str, minio_path: str, bucket_name: str) -> str:
        """Upload file to case-specific MinIO bucket."""
        try:
            print(f"Uploading {file_path} to case bucket {bucket_name} at {minio_path}...")
            self._minio_client.fput_object(
                bucket_name, minio_path, file_path
            )
            print(f"Successfully uploaded to case bucket: {minio_path}")
            return minio_path
        except S3Error as e:
            print(f"MinIO upload error: {e}")
            raise RuntimeError(f"Failed to upload file to case bucket: {e}")
        except Exception as e:
            print(f"Unexpected error in _upload_file_to_case_bucket: {e}")
            raise RuntimeError(f"Failed to upload file to case bucket: {e}")

    async def _insert_case_record(self, case_id: str, case_name: str, bucket_url: str):
        """Insert case record into database with bucket URL."""
        try:
            print(f"Inserting case record: id={case_id}, name={case_name}, bucket={bucket_url}")
            async with self._pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO cases(id, name, bucket_url, created_at)
                    VALUES($1, $2, $3, now())
                    """,
                    case_id, case_name, bucket_url
                )
            print(f"Successfully inserted case record for {case_id}")
        except Exception as e:
            print(f"Database insertion error: {e}")
            raise RuntimeError(f"Failed to insert case record: {e}")

    async def _ensure_case_bucket_exists(self, bucket_name: str):
        """Ensure the case-specific MinIO bucket exists."""
        try:
            if not self._minio_client.bucket_exists(bucket_name):
                self._minio_client.make_bucket(bucket_name)
                print(f"Created case bucket: {bucket_name}")
            else:
                print(f"Case bucket already exists: {bucket_name}")
        except S3Error as e:
            raise RuntimeError(f"Failed to create case bucket {bucket_name}: {e}")

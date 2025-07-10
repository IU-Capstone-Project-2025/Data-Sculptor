import os
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio

import boto3
import docker
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class DockerSpawnerService:
    """Service for spawning Docker containers from S3 images."""
    
    def __init__(self, bucket_name: str, region: str):
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.docker_client = docker.from_env()
        
    async def spawn_container(
        self, 
        case_id: str, 
        container_name: Optional[str] = None,
        port_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Spawn a Docker container from an S3 image.
        
        Args:
            case_id: The case ID used to construct the S3 key
            container_name: Optional custom name for the container
            port_mapping: Optional port mapping (host_port: container_port)
        
        Returns:
            Dict containing container_id and status information
        """
        try:
            # Construct S3 key based on case_id
            s3_key = f"{case_id}/image.tar"
            
            # Download image from S3
            image_path = await self._download_image_from_s3(s3_key)
            
            # Load the Docker image
            image_name = await self._load_docker_image(image_path)
            
            # Run the container
            container = await self._run_container(
                image_name, 
                container_name, 
                port_mapping
            )
            
            return {
                "container_id": container.id,
                "container_name": container.name,
                "image_name": image_name,
                "status": "running"
            }
            
        except Exception as e:
            logger.error(f"Error spawning container for case {case_id}: {str(e)}")
            raise
    
    async def _download_image_from_s3(self, s3_key: str) -> str:
        """
        Download Docker image from S3.
        
        Args:
            s3_key: The S3 key for the image file
        
        Returns:
            Path to the downloaded image file
        """
        try:
            # Create temporary file for the image
            temp_file = tempfile.NamedTemporaryFile(suffix='.tar', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            logger.info(f"Downloading image from s3://{self.bucket_name}/{s3_key}")
            
            # Download file from S3
            self.s3_client.download_file(self.bucket_name, s3_key, temp_path)
            
            logger.info(f"Image downloaded successfully to {temp_path}")
            return temp_path
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise ValueError(f"Image not found in S3: s3://{self.bucket_name}/{s3_key}")
            elif e.response['Error']['Code'] == 'NoSuchBucket':
                raise ValueError(f"S3 bucket not found: {self.bucket_name}")
            else:
                raise Exception(f"S3 error: {str(e)}")
        except NoCredentialsError:
            raise Exception("AWS credentials not configured")
        except Exception as e:
            raise Exception(f"Error downloading image: {str(e)}")
    
    async def _load_docker_image(self, image_path: str) -> str:
        """
        Load Docker image from tar file.
        
        Args:
            image_path: Path to the .tar file
        
        Returns:
            Name of the loaded image
        """
        try:
            logger.info(f"Loading Docker image from {image_path}")
            
            # Load the image using docker load
            with open(image_path, 'rb') as f:
                self.docker_client.images.load(f)
            
            # Get the loaded image name
            # We'll use a simple approach - get the first image that was recently loaded
            images = self.docker_client.images.list()
            if not images:
                raise Exception("No images found after loading")
            
            # Get the most recently created image
            latest_image = max(images, key=lambda img: img.attrs['Created'])
            image_name = latest_image.tags[0] if latest_image.tags else latest_image.id
            
            logger.info(f"Docker image loaded successfully: {image_name}")
            return image_name
            
        except Exception as e:
            raise Exception(f"Error loading Docker image: {str(e)}")
        finally:
            # Clean up the temporary file
            try:
                os.unlink(image_path)
            except OSError:
                pass
    
    async def _run_container(
        self, 
        image_name: str, 
        container_name: Optional[str] = None,
        port_mapping: Optional[Dict[str, str]] = None
    ):
        """
        Run a Docker container.
        
        Args:
            image_name: Name of the Docker image to run
            container_name: Optional custom name for the container
            port_mapping: Optional port mapping
        
        Returns:
            Docker container object
        """
        try:
            # Prepare run parameters
            run_params = {
                "detach": True,
                "remove": False,  # Don't auto-remove so we can manage it
            }
            
            if container_name:
                run_params["name"] = container_name
            
            if port_mapping:
                run_params["ports"] = port_mapping
            
            logger.info(f"Running container from image: {image_name}")
            
            # Run the container
            container = self.docker_client.containers.run(image_name, **run_params)
            
            logger.info(f"Container started successfully: {container.id}")
            return container
            
        except Exception as e:
            raise Exception(f"Error running container: {str(e)}")
    
    async def get_container_status(self, container_id: str) -> Dict[str, Any]:
        """
        Get the status of a running container.
        
        Args:
            container_id: The ID of the container
        
        Returns:
            Dict with container status information
        """
        try:
            container = self.docker_client.containers.get(container_id)
            container.reload()  # Refresh container info
            
            # Get port bindings
            ports = {}
            if container.attrs.get('NetworkSettings', {}).get('Ports'):
                for container_port, host_bindings in container.attrs['NetworkSettings']['Ports'].items():
                    if host_bindings:
                        ports[container_port] = host_bindings[0]['HostPort']
            
            return {
                "container_id": container_id,
                "status": container.status,
                "running": container.status == "running",
                "ports": ports,
                "logs": container.logs().decode('utf-8') if container.status == "running" else None
            }
            
        except docker.errors.NotFound:
            raise ValueError(f"Container {container_id} not found")
        except Exception as e:
            raise Exception(f"Error getting container status: {str(e)}")
    
    async def stop_container(self, container_id: str):
        """
        Stop and remove a container.
        
        Args:
            container_id: The ID of the container to stop
        """
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Stop the container if it's running
            if container.status == "running":
                container.stop()
                logger.info(f"Container {container_id} stopped")
            
            # Remove the container
            container.remove()
            logger.info(f"Container {container_id} removed")
            
        except docker.errors.NotFound:
            raise ValueError(f"Container {container_id} not found")
        except Exception as e:
            raise Exception(f"Error stopping container: {str(e)}")
    
    async def list_containers(self) -> list:
        """
        List all containers managed by this service.
        
        Returns:
            List of container information
        """
        try:
            containers = self.docker_client.containers.list(all=True)
            return [
                {
                    "id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else container.image.id
                }
                for container in containers
            ]
        except Exception as e:
            raise Exception(f"Error listing containers: {str(e)}") 
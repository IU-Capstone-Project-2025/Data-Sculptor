#!/usr/bin/env python3
"""
Simple MinIO browser script
"""

from minio import Minio
from minio.error import S3Error

def browse_minio():
    # Initialize MinIO client
    minio_client = Minio(
        "localhost:52298",  # Replace with your MinIO endpoint
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False  # Set to True if using HTTPS
    )
    
    try:
        # List all buckets
        print("=== Available Buckets ===")
        buckets = minio_client.list_buckets()
        for bucket in buckets:
            print(f"Bucket: {bucket.name}")
            
            # List objects in each bucket
            try:
                objects = minio_client.list_objects(bucket.name, recursive=True)
                for obj in objects:
                    print(f"  - {obj.object_name} ({obj.size} bytes)")
            except S3Error as e:
                print(f"  Error listing objects: {e}")
        
        print("\n=== Bucket Details ===")
        for bucket in buckets:
            print(f"\nBucket: {bucket.name}")
            try:
                # Count objects
                objects = list(minio_client.list_objects(bucket.name, recursive=True))
                print(f"  Objects: {len(objects)}")
                
                # Show object details
                for obj in objects:
                    print(f"    - {obj.object_name}")
                    print(f"      Size: {obj.size} bytes")
                    print(f"      Last Modified: {obj.last_modified}")
                    
            except S3Error as e:
                print(f"  Error getting bucket info: {e}")
                
    except S3Error as e:
        print(f"Error connecting to MinIO: {e}")

if __name__ == "__main__":
    browse_minio() 
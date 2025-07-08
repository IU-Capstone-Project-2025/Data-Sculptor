#!/usr/bin/env python3
"""
Test script for case upload functionality.
This script uploads the test files to test the case upload endpoint.
"""

import asyncio
import aiohttp
import os
from pathlib import Path


async def test_case_upload():
    """Test the case upload endpoint with the test files."""
    
    # Get the test directory
    test_dir = Path(__file__).parent
    
    # Prepare the multipart form data
    data = aiohttp.FormData()
    
    # Add test files
    files_to_upload = {
        'requirements': test_dir / 'requirements.txt',
        'dataset': test_dir / 'dataset.csv',
        'profile': test_dir / 'profile.ipynb',
        'template': test_dir / 'template.ipynb'
    }
    
    # Check if all files exist
    for name, file_path in files_to_upload.items():
        if not file_path.exists():
            print(f"❌ Test file not found: {file_path}")
            return
        print(f"✅ Found test file: {file_path}")
    
    # Add files to form data
    for name, file_path in files_to_upload.items():
        data.add_field(name, open(file_path, 'rb'), filename=file_path.name)
    
    # Upload to the service
    async with aiohttp.ClientSession() as session:
        url = "http://10.100.30.239:51804/api/v1/upload_case/test-data-analysis"
        
        try:
            print(f"\n🚀 Uploading to: {url}")
            async with session.post(url, data=data) as response:
                if response.status == 201:
                    result = await response.json()
                    print(f"✅ Case upload successful!")
                    print(f"Case ID: {result.get('case_id')}")
                    print(f"Status: {result.get('status_code')}")
                else:
                    error_text = await response.text()
                    print(f"❌ Case upload failed with status {response.status}")
                    print(f"Error: {error_text}")
        except Exception as e:
            print(f"❌ Error during upload: {e}")


async def test_health_check():
    """Test the health check endpoint."""
    async with aiohttp.ClientSession() as session:
        url = "http://10.100.30.239:51804/api/v1/health"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Health check successful: {result}")
                else:
                    print(f"❌ Health check failed: {response.status}")
        except Exception as e:
            print(f"❌ Health check error: {e}")


async def main():
    """Run all tests."""
    print("🧪 Testing Profile Uploader Service")
    print("=" * 50)
    
    # Test health check first
    print("\n1. Testing health check...")
    await test_health_check()
    
    # Test case upload
    print("\n2. Testing case upload...")
    await test_case_upload()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")


if __name__ == "__main__":
    print("Starting tests...")
    asyncio.run(main()) 
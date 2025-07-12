#!/usr/bin/env python3
"""
Browse Docker image tar file contents
"""

import tarfile
import json
import sys
from pathlib import Path

def browse_docker_tar(tar_path):
    """Browse contents of a Docker image tar file."""
    
    if not Path(tar_path).exists():
        print(f"Error: File {tar_path} not found")
***REMOVED***
    
    print(f"=== Browsing Docker Image: {tar_path} ===")
    
    with tarfile.open(tar_path, 'r') as tar:
        # List all members
        members = tar.getmembers()
        print(f"Total files: {len(members)}")
        
        # Find manifest.json
        manifest_files = [m for m in members if m.name.endswith('manifest.json')]
        
        if manifest_files:
            print("\n=== Docker Manifest ===")
            manifest_file = manifest_files[0]
            manifest_data = tar.extractfile(manifest_file)
            if manifest_data:
                manifest = json.load(manifest_data)
                for layer in manifest:
                    print(f"Layer: {layer.get('Config', 'Unknown')}")
                    print(f"RepoTags: {layer.get('RepoTags', [])}")
                    print(f"Layers: {layer.get('Layers', [])}")
                    print()
        
        # Find config.json
        config_files = [m for m in members if m.name.endswith('config.json')]
        
        if config_files:
            print("=== Docker Config ===")
            config_file = config_files[0]
            config_data = tar.extractfile(config_file)
            if config_data:
                config = json.load(config_data)
                print(f"Architecture: {config.get('architecture', 'Unknown')}")
                print(f"OS: {config.get('os', 'Unknown')}")
                print(f"Created: {config.get('created', 'Unknown')}")
                print(f"Author: {config.get('author', 'Unknown')}")
                
                # Show environment variables
                env = config.get('config', {}).get('Env', [])
                if env:
                    print("\nEnvironment Variables:")
                    for var in env:
                        print(f"  {var}")
                
                # Show working directory
                workdir = config.get('config', {}).get('WorkingDir', 'Unknown')
                print(f"\nWorking Directory: {workdir}")
                
                # Show entrypoint
                entrypoint = config.get('config', {}).get('Entrypoint', [])
                if entrypoint:
                    print(f"Entrypoint: {entrypoint}")
                
                # Show cmd
                cmd = config.get('config', {}).get('Cmd', [])
                if cmd:
                    print(f"CMD: {cmd}")
        
        # Show layer contents
        print("\n=== Layer Contents ===")
        layer_dirs = [m for m in members if m.name.endswith('/layer.tar')]
        
        for layer_dir in layer_dirs[:3]:  # Show first 3 layers
            print(f"\nLayer: {layer_dir.name}")
            try:
                layer_tar = tar.extractfile(layer_dir)
                if layer_tar:
                    with tarfile.open(fileobj=layer_tar, mode='r') as layer:
                        # Show some files from this layer
                        files = layer.getmembers()[:10]  # First 10 files
                        for file in files:
                            print(f"  {file.name} ({file.size} bytes)")
                        if len(layer.getmembers()) > 10:
                            print(f"  ... and {len(layer.getmembers()) - 10} more files")
            except Exception as e:
                print(f"  Error reading layer: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python browse_tar.py <path_to_image.tar>")
        print("Example: python browse_tar.py /tmp/case-123.tar")
        sys.exit(1)
    
    tar_path = sys.argv[1]
    browse_docker_tar(tar_path)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Script to download a model from HuggingFace to the server.
"""

import sys
import os
from pathlib import Path
from huggingface_hub import snapshot_download

def download_model(model_name: str, target_dir: str) -> None:
    """
    Download a model from HuggingFace.
    
    Args:
        model_name: Name of the model (e.g., "meta-llama/Llama-3.1-8B-Instruct")
        target_dir: Target directory to save the model (will be expanded with ~)
    """
    # Expand ~ in target directory
    target_path = Path(target_dir).expanduser()
    # Preserve original model name structure (e.g., "meta-llama/Llama-3.1-8B-Instruct")
    model_path = target_path / model_name
    
    print(f"📥 Downloading model: {model_name}")
    print(f"📁 Target directory: {model_path}")
    
    # Create target directory if it doesn't exist
    model_path.mkdir(parents=True, exist_ok=True)
    
    # Token only if non-empty; empty string becomes "Bearer " and breaks HTTP clients
    raw = os.environ.get("HF_TOKEN")
    hf_token = (raw.strip() if raw else None) or None

    try:
        # Download the model
        print(f"⏳ Starting download...")
        snapshot_download(
            repo_id=model_name,
            local_dir=str(model_path),
            token=hf_token,
            resume_download=True,
            local_dir_use_symlinks=False
        )
        
        print(f"✅ Model downloaded successfully!")
        print(f"📁 Location: {model_path}")
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 download_model.py <model_name> <target_dir>")
        print('Example: python3 download_model.py "meta-llama/Llama-3.1-8B-Instruct" "~/models"')
        sys.exit(1)
    
    model_name = sys.argv[1]
    target_dir = sys.argv[2]
    
    download_model(model_name, target_dir)

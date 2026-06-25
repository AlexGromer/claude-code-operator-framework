#!/usr/bin/env python3
"""
Ollama Manager - Local LLM Management Tool

Manages Ollama models and provides integration patterns.
Addresses GAP-LOCAL-001: Ollama detailed guide.
"""

import subprocess
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from pathlib import Path


@dataclass
class OllamaModel:
    """Ollama model information."""
    name: str
    size: str
    modified: str
    digest: str


@dataclass  
class OllamaResponse:
    """Response from Ollama API."""
    model: str
    response: str
    total_duration: int
    prompt_eval_count: int
    eval_count: int


class OllamaManager:
    """
    Manager for Ollama local LLM operations.
    
    Features:
    - Model listing and management
    - GPU configuration
    - API integration patterns
    - Performance monitoring
    """
    
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self.models_dir = Path.home() / ".ollama" / "models"
        
    def is_running(self) -> bool:
        """Check if Ollama is running."""
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self.host}/api/tags"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def list_models(self) -> List[OllamaModel]:
        """List available models."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return []
            
            models = []
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    models.append(OllamaModel(
                        name=parts[0],
                        digest=parts[1],
                        size=parts[2],
                        modified=parts[3] if len(parts) > 3 else ""
                    ))
            return models
        except Exception:
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def run_prompt(self, model: str, prompt: str) -> Optional[OllamaResponse]:
        """Run a prompt against a model."""
        try:
            import requests
            response = requests.post(
                f"{self.host}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=120
            )
            if response.status_code == 200:
                data = response.json()
                return OllamaResponse(
                    model=data.get("model", model),
                    response=data.get("response", ""),
                    total_duration=data.get("total_duration", 0),
                    prompt_eval_count=data.get("prompt_eval_count", 0),
                    eval_count=data.get("eval_count", 0)
                )
        except Exception:
            pass
        return None
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed model information."""
        try:
            result = subprocess.run(
                ["ollama", "show", model_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return {"output": result.stdout}
        except Exception:
            pass
        return None
    
    def delete_model(self, model_name: str) -> bool:
        """Delete a model."""
        try:
            result = subprocess.run(
                ["ollama", "rm", model_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information for Ollama."""
        info = {
            "cuda_available": False,
            "gpu_count": 0,
            "gpu_memory": []
        }
        
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
                 "--format=csv,noheader"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                info["cuda_available"] = True
                gpus = result.stdout.strip().split('\n')
                info["gpu_count"] = len(gpus)
                for gpu in gpus:
                    parts = gpu.split(',')
                    if len(parts) >= 3:
                        info["gpu_memory"].append({
                            "name": parts[0].strip(),
                            "total": parts[1].strip(),
                            "free": parts[2].strip()
                        })
        except Exception:
            pass
        
        return info
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive Ollama status."""
        return {
            "running": self.is_running(),
            "host": self.host,
            "models": [m.__dict__ for m in self.list_models()],
            "gpu": self.get_gpu_info()
        }


# Integration patterns
OLLAMA_PATTERNS = {
    "langchain": """
from langchain_community.llms import Ollama
llm = Ollama(model="llama3")
response = llm.invoke("Hello, world!")
""",
    "litellm": """
import litellm
response = litellm.completion(
    model="ollama/llama3",
    messages=[{"role": "user", "content": "Hello!"}]
)
""",
    "openai_compatible": """
from openai import OpenAI
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
response = client.chat.completions.create(
    model="llama3",
    messages=[{"role": "user", "content": "Hello!"}]
)
"""
}


def get_recommended_models() -> List[Dict[str, str]]:
    """Get recommended models for different use cases."""
    return [
        {"name": "llama3:8b", "use_case": "General purpose, good balance"},
        {"name": "codellama:7b", "use_case": "Code generation"},
        {"name": "mistral:7b", "use_case": "Fast, efficient"},
        {"name": "phi3:mini", "use_case": "Lightweight, edge deployment"},
        {"name": "gemma2:9b", "use_case": "Google's efficient model"},
        {"name": "qwen2:7b", "use_case": "Multilingual, Chinese support"}
    ]


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ollama Manager")
    parser.add_argument("--status", action="store_true", help="Show Ollama status")
    parser.add_argument("--list", action="store_true", help="List models")
    parser.add_argument("--pull", type=str, help="Pull a model")
    parser.add_argument("--run", type=str, help="Run prompt with model")
    parser.add_argument("--prompt", type=str, default="Hello!", help="Prompt text")
    parser.add_argument("--patterns", action="store_true", help="Show integration patterns")
    
    args = parser.parse_args()
    manager = OllamaManager()
    
    if args.status:
        status = manager.get_status()
        print(json.dumps(status, indent=2))
    
    elif args.list:
        models = manager.list_models()
        for model in models:
            print(f"{model.name}: {model.size}")
    
    elif args.pull:
        success = manager.pull_model(args.pull)
        print(f"Pull {'successful' if success else 'failed'}")
    
    elif args.run:
        response = manager.run_prompt(args.run, args.prompt)
        if response:
            print(f"Response: {response.response}")
            print(f"Duration: {response.total_duration/1e9:.2f}s")
    
    elif args.patterns:
        for name, pattern in OLLAMA_PATTERNS.items():
            print(f"\n=== {name.upper()} ===")
            print(pattern)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

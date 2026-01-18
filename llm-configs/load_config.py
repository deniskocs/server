#!/usr/bin/env python3
"""
Скрипт для загрузки конфигурации из YAML файла и генерации параметров командной строки для vLLM.
"""

import sys
import yaml
import os

def load_config(config_path):
    """Загружает конфигурацию из YAML файла."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def build_vllm_args(config):
    """Строит аргументы командной строки для vLLM на основе конфигурации."""
    args = []
    vllm_config = config.get('vllm', {})
    
    # Добавляем параметры только если они указаны (не null)
    if vllm_config.get('quantization'):
        args.append(f"--quantization {vllm_config['quantization']}")
    
    if vllm_config.get('max_model_len'):
        args.append(f"--max-model-len {vllm_config['max_model_len']}")
    
    if vllm_config.get('dtype'):
        args.append(f"--dtype {vllm_config['dtype']}")
    
    if vllm_config.get('gpu_memory_utilization') is not None:
        args.append(f"--gpu-memory-utilization {vllm_config['gpu_memory_utilization']}")
    
    if vllm_config.get('enable_auto_tool_choice'):
        args.append("--enable-auto-tool-choice")
    
    if vllm_config.get('tool_call_parser'):
        args.append(f"--tool-call-parser {vllm_config['tool_call_parser']}")
    
    return ' '.join(args)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 load_config.py <config_file>", file=sys.stderr)
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    
    config = load_config(config_path)
    
    # Выводим имя модели по умолчанию
    model_config = config.get('model', {})
    default_model = model_config.get('default_name', '')
    if default_model:
        print(f"DEFAULT_MODEL_NAME={default_model}")
    
    # Выводим имя модели для served-model-name (по умолчанию используем default_name)
    served_model_name = model_config.get('served_name', default_model)
    if served_model_name:
        print(f"SERVED_MODEL_NAME={served_model_name}")
    
    # Выводим аргументы vLLM
    vllm_args = build_vllm_args(config)
    print(f"VLLM_ARGS={vllm_args}")

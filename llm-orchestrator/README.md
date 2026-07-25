# llm-orchestrator

Docker-образы inference для k8s GitOps:

- [`vllm-runner/`](vllm-runner/) — vLLM OpenAI API (`Dockerfile.decarf`)
- [`hidream-runner/`](hidream-runner/) — HiDream Dev-2604 T2I (`POST /v1/images/generations`, `/health`)
- CI: [build-vllm-runner](../.github/workflows/build-vllm-runner.yaml), [build-hidream-runner](../.github/workflows/build-hidream-runner.yaml)
- Deployments: [`infra/k8s/llms/`](../infra/k8s/llms/)

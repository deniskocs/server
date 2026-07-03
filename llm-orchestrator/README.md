# llm-orchestrator

Остался только Docker-образ vLLM для k8s GitOps:

- [`vllm-runner/`](vllm-runner/) — `Dockerfile.decarf`, `docker-entrypoint.sh`
- CI: [`.github/workflows/build-vllm-runner.yaml`](../.github/workflows/build-vllm-runner.yaml)
- Deployments: [`infra/k8s/llms/`](../infra/k8s/llms/)

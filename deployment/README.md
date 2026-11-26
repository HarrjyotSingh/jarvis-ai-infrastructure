# Deployment configuration

These examples show how the four nodes in [the topology](../README.md#architecture) fit together. The storage stack is runnable with upstream images and fresh volumes. The inference launcher needs a compatible vLLM build and model files. The speech unit shows how the two FastAPI workers are supervised.

| Node | Configuration | Role in the live setup |
| --- | --- | --- |
| AI inference | [vLLM launcher](inference/serve-vllm.sh) | Serves Qwen3.8 to OpenCode and DSH. The settings retain FP8 KV cache and the three-sequence cap from the GPU host. |
| Senses | [Speech API unit](senses/jarvis-speech%40.service) | Runs Faster-Whisper for transcription and Piper for speech, alongside separate embedding and search services. |
| Storage and automation | [Docker Compose](storage/compose.yaml), [Chroma proxy](storage/chroma-proxy.conf) | Runs ChromaDB and n8n with persistent volumes and a 1.25 GiB cap on n8n. |
| Developer workstation | [OpenCode provider](clients/opencode.example.json), [DSH provider](clients/dsh-provider.example.yaml) | Both use the same OpenAI-compatible endpoint. |
| Hermes backend on the inference node | [SSH workspace registry](clients/workspace-config.example.json) | Lists the SSH hosts and workspace roots. Endpoints are tried in Ethernet-first order where both routes exist. |

## Run the storage sample

Use Docker Compose and OpenSSL. Generate the n8n key once as the user running the sample. The container must be able to read the key file. Keep a secure backup of the key with the data volume so restored credentials remain readable.

```sh
cd deployment/storage
mkdir -p .secrets
(umask 077; set -C; openssl rand -hex 32 > .secrets/n8n-encryption-key)
docker compose up -d
curl --fail http://127.0.0.1:8000/api/v2/heartbeat
```

The n8n UI is at `http://localhost:5678`. ChromaDB itself has no published port. The proxy and n8n bind to loopback on the host. n8n can reach Chroma directly at `http://chroma:8000` over the internal network. Use `docker compose down` to stop the sample and keep the volumes. The sample starts with empty data and workflows.

## Use the other examples

- Set `VLLM_MODEL_DIR` and `VLLM_API_KEY` before running the inference launcher. Use a ROCm/vLLM build that can load your model artifacts. The context and GPU-memory settings are tunable for smaller devices. Point OpenCode's `JARVIS_MODEL_BASE_URL` and the DSH provider's `baseURL` at the private `/v1` endpoint. The OpenCode example uses the provider schema from the workstation's 1.19.6 client.
- The speech unit expects an `app:app` FastAPI entry point and a virtual environment for each instance under `~/services/jarvis/stt` and `~/services/jarvis/tts`. Each instance reads its own port from `~/.config/jarvis/stt.env` or `tts.env`. Supply the worker applications and model files before installing the unit.
- Add the SSH workspaces through Hermes Desktop or use the registry as a reference. Replace the example user, endpoints, and absolute workspace roots with values for your lab. Verify each host key through a trusted channel before connecting.

## Security controls

- **Network access.** The live cluster uses wired Ethernet for local service traffic and Tailscale for private remote access and fallback. ChromaDB runs behind a separate proxy, and the vLLM container has no direct host port mapping. Tailscale encrypts tailnet traffic with WireGuard and provides HTTPS for configured web ingress. The public examples default to loopback or an internal Docker network. [Tailscale encryption](https://tailscale.com/security-policies/encryption-cryptography)
- **OpenSSH.** Hermes Workspaces uses system-managed SSH keys with `StrictHostKeyChecking=yes` and `BatchMode=yes`. Workspace roots bound file access, and stale revisions are rejected before atomic writes. [Plugin implementation and tests](../integrations/hermes-ssh-workspaces)
- **Vault access.** The deployed Obsidian Gateway checks a bearer token, validates paths under the vault root, and checks a note's revision before overwriting it.
- **Runtime secrets.** The storage example mounts the n8n encryption key as a Compose secret. The inference launcher and clients read their key from the environment. The repository uses example hostnames and empty volumes. [Docker Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/)
- **Remote exposure.** For a new installation, keep model and database backends on loopback or private interfaces. Restrict any remote ingress to the users and devices that need it. vLLM API keys protect selected routes, so keep the gateway or network boundary in place. [vLLM security guidance](https://docs.vllm.ai/en/latest/usage/security/)

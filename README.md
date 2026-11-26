# Jarvis AI Infrastructure

I built Jarvis as a self-hosted AI setup across several Linux machines. It keeps an Obsidian knowledge index up to date and serves retrieval to a local assistant. I separated storage and automation from embedding and inference so the storage host could run on older hardware.

This portfolio repo contains a small, runnable version of incremental retrieval using synthetic notes. It also pins the public Hermes Desktop plugin I use to browse and edit files in remote workspaces over SSH.

## Architecture

![Jarvis topology showing the workstation, GPU inference server, speech and embedding node, and storage and automation node](docs/jarvis-architecture.png)

[Editable Excalidraw source](docs/jarvis-architecture.excalidraw) · Open in Excalidraw's dark theme.

OpenCode and DSH use the same Qwen3.8 endpoint on the inference server. Hermes Desktop connects to the Hermes backend, where the SSH Workspaces plugin opens files on the other nodes. The wired network carries traffic between the machines, with Tailscale for remote access and configured fallback routes.

## Setup and security

The deployment examples show the vLLM launch settings, the ChromaDB and n8n storage stack, and the client configs that connect to the cluster. The guide covers the private network routes, OpenSSH controls, vault access checks, and runtime secrets. [Configuration and security guide](deployment/README.md)

## Nodes and resource use

Three server nodes stay on for inference, speech and embeddings, and storage. I spread those workloads across machines so a burst of model requests or indexing uses a separate RAM budget from ChromaDB and n8n. The workstation handles interactive work and can take extra GPU jobs on demand.

### Node 1 · AI inference

| Resource | Live setup |
| --- | --- |
| Hardware | 16 GB RAM · Radeon AI PRO R9700 with 32 GB VRAM · Ubuntu |
| Always-on services | vLLM serves Qwen3.8. Hermes, Obsidian Gateway, and Nextcloud AIO also run here. |
| Spike controls | vLLM uses an FP8 KV cache and allows up to three concurrent sequences. Docker caps the Nextcloud app at 1 GiB and its database at 768 MiB. This host uses disk-backed swap. |

### Node 2 · Senses and embeddings

| Resource | Live setup |
| --- | --- |
| Hardware | 16 GB RAM · GeForce GTX 1650 with 4 GB VRAM · CachyOS |
| Always-on services | BGE-M3 and MobileCLIP serve embeddings. Faster-Whisper, Piper, and SearXNG run on this node. |
| Spike controls | The indexer sends batches of up to 16 text chunks or one visual item. zram absorbs some of the short-term RAM pressure when jobs overlap. |

### Node 3 · Storage and automation

| Resource | Live setup |
| --- | --- |
| Hardware | 8 GB RAM · dual-core Intel i3 · Debian |
| Always-on services | ChromaDB holds the vector index and n8n runs workflows. The node keeps a vault replica and runs the Nextcloud office and preview workers. |
| Spike controls | Docker caps n8n at 1.25 GiB. The office worker is capped at 768 MiB and the preview worker at 640 MiB. zram handles compressed swap, with disk swap also available. |

### Node 4 · Developer workstation

| Resource | Live setup |
| --- | --- |
| Hardware | 32 GB RAM · GeForce RTX 4070 with 8 GB VRAM · CachyOS |
| Client workloads | OpenCode and DSH connect to the inference server. Hermes Desktop opens remote workspaces and Syncthing keeps a local vault copy. |
| Overflow | I start and stop optional GPU jobs here to leave the server workloads running. The workstation also uses zram. |

### How I handle spikes

zram stores swapped pages compressed in RAM. In one check on the Senses node, about 3.9 GiB of pages occupied 2.2 GiB of physical memory, including overhead. Compression varies with the workload. [Linux kernel zram documentation](https://docs.kernel.org/admin-guide/blockdev/zram.html)

Before starting an extra job, I check `MemAvailable` during a busy period. The runbook budgets the job's upper limit plus a 4 GiB host reserve. If a node is already swapping heavily, I defer the job or move it to the workstation when it fits there.

## Run the retrieval demo

The Compose demo runs the retrieval flow locally using synthetic notes. It uses a CPU embedding model to show how one note edit updates the search result.

With Docker and Docker Compose installed, run these commands from the repository root.

```sh
docker compose up -d chroma
docker compose run --rm --build demo
docker compose down
```

The demo container downloads about 80 MB of public MiniLM model weights when it starts. ChromaDB runs in a separate container and is reachable from the demo over the Compose network. The Compose file publishes no ports to the host.

The demo indexes three synthetic notes and retrieves a note about greenhouse irrigation. A second sync writes zero vectors. The demo changes the sprinkler material from brass to stainless steel, reindexes only that note, and checks that the same question returns the updated text. It then deletes another note and checks that it disappears from the index.

The [indexer](demo/retrieval.py) stores a SHA-256 hash with each document so it can skip unchanged content. It uses one vector per short note and scans the small demo collection on each run. The demo creates and cleans up a dedicated collection.

## Explore the Hermes plugin

[Hermes SSH Workspaces](https://github.com/HarrjyotSingh/hermes-ssh-workspaces) adds local and SSH-backed file browsing and editing to Hermes Desktop. This repo pins it as an optional Git submodule. Run `git submodule update --init` to inspect the pinned source locally, or follow the link for its separate installation instructions.

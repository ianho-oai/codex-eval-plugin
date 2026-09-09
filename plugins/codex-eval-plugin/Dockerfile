# Build once, then pin the resulting image ID using `codex-eval image-pin`.
# Rebuilding can update OS packages; only the recorded image digest is reproducible.
FROM node:22.16.0-bookworm-slim
ARG CODEX_VERSION=0.153.4
ARG CLAUDE_VERSION=2.1.220
RUN apt-get update && apt-get install -y --no-install-recommends python3 git ca-certificates ripgrep \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @openai/codex@${CODEX_VERSION} @anthropic-ai/claude-code@${CLAUDE_VERSION} \
    && npm cache clean --force
ENV PYTHONDONTWRITEBYTECODE=1 DISABLE_AUTOUPDATER=1
WORKDIR /workspace

# syntax=docker/dockerfile:1
# speech-to-sheets for a Linux server. Build from the repo root:
#   docker build -f deploy/docker/Dockerfile -t speech-to-sheets .
# Run it with deploy/docker/compose.yaml; see the README, Run it on a Linux server.

# Every stage starts from the same image, so whisper-cli is built against the same Debian
# (glibc, libstdc++) that runs it.
ARG PYTHON_IMAGE=python:3.12.15-slim-trixie

# ---- Stage 1: build whisper-cli from a pinned whisper.cpp release ----
FROM ${PYTHON_IMAGE} AS whisper
ARG WHISPER_VERSION=v1.9.5
# The commit that tag pointed to when this file was written; the build stops if the tag moves.
ARG WHISPER_COMMIT=d1be6fde11ac6e0407606b4e42fe72d34add8037
# ON tunes whisper-cli for the CPU of the machine that builds the image: fastest, but on an
# older or different CPU it can crash with "illegal instruction". So build the image on the
# server that runs it. OFF gives a slower binary that runs on any CPU of the same
# architecture (on x86 it still needs AVX2): --build-arg GGML_NATIVE=OFF
ARG GGML_NATIVE=ON

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch "$WHISPER_VERSION" \
        https://github.com/ggml-org/whisper.cpp.git /whisper.cpp \
    && test "$(git -C /whisper.cpp rev-parse HEAD)" = "$WHISPER_COMMIT"
WORKDIR /whisper.cpp
# Static libraries, so the binary is the only file to copy. OpenMP stays on (it spreads the
# work over all CPU cores); the final stage installs its runtime library, libgomp1.
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
        -DGGML_NATIVE="$GGML_NATIVE" -DGGML_CCACHE=OFF \
        -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_SERVER=OFF \
    && cmake --build build --target whisper-cli -j "$(nproc)" \
    && install -m 0755 build/bin/whisper-cli /usr/local/bin/whisper-cli

# ---- Stage 2: install the app and its locked dependencies into a virtual environment ----
FROM ${PYTHON_IMAGE} AS app
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv
# Use the image's Python, never a downloaded one. Compile .pyc files now, because the bot
# cannot write into /opt/venv at runtime. Copy from the cache mount instead of linking.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.12 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /build
# Dependencies first, in their own layer, so a code change does not reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project
COPY src ./src
# --no-editable installs a copy of the app, so /build is not needed after this stage.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ---- Stage 3: the image that runs the bot ----
FROM ${PYTHON_IMAGE}
# ffmpeg converts voice notes to wav; libgomp1 is the OpenMP library whisper-cli needs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=whisper /usr/local/bin/whisper-cli /usr/local/bin/whisper-cli
COPY --from=app /opt/venv /opt/venv
# whisper-cli, ffmpeg and speech-to-sheets are all on PATH, so the default config values work.
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

# The bot runs as this unprivileged user. The data folder mounted at /data must be
# readable and writable by this user ID: sudo chown -R 10001:10001 <data folder>
ARG APP_UID=10001
RUN groupadd --gid "$APP_UID" speech-to-sheets \
    && useradd --uid "$APP_UID" --gid "$APP_UID" --home-dir /data --no-create-home \
        --shell /usr/sbin/nologin speech-to-sheets \
    && install -d -o "$APP_UID" -g "$APP_UID" -m 0700 /data

# config.yaml, .env, the model and dedupe.sqlite live here; relative paths in config.yaml
# resolve from this folder.
WORKDIR /data
VOLUME /data
USER ${APP_UID}:${APP_UID}
# Python turns SIGINT into a clean shutdown; as process 1 it would ignore Docker's SIGTERM.
STOPSIGNAL SIGINT
CMD ["speech-to-sheets", "run"]

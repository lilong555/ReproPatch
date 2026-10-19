FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ cmake make python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
USER 65534:65534
WORKDIR /build
# No source, model client, credentials or Docker socket is baked into the image.

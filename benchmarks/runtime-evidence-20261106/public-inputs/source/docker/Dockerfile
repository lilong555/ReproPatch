FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ cmake make ninja-build ccache python3 bash ripgrep ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
USER 65534:65534
WORKDIR /build
# 镜像仅包含工具链，源码与执行资源由每次运行提供。

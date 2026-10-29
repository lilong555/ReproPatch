FROM ghcr.io/lilong555/repropatch-cross-cpp@sha256:688d9f65c08c283a203d1ff03e7fc60f8b57167cfa925eaa26fb70d2d8b94533
USER root
RUN apt-get update && apt-get install -y --no-install-recommends gdb llvm-19-dev \
    && ln -s /usr/bin/clang-19 /usr/local/bin/clang \
    && ln -s /usr/bin/clang++-19 /usr/local/bin/clang++ \
    && rm -rf /var/lib/apt/lists/*
USER 65534:65534
WORKDIR /build

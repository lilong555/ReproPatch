FROM ghcr.io/lilong555/repropatch-cross-cpp@sha256:7131796ef11523e09332f798cb50e5ce7a723d8da9d1e99a0927a83337588f4b AS llvm_input
ADD --checksum=sha256:f5226f82f26712752af6e0040195fad3f097131aaddac76fa64ecfaa7cc64193 \
    https://github.com/shader-slang/slang/releases/download/v2025.12.1/slang-2025.12.1-linux-x86_64.zip /tmp/slang-llvm.zip
RUN python3 -c "import zipfile; from pathlib import Path; z=zipfile.ZipFile('/tmp/slang-llvm.zip'); names=[n for n in z.namelist() if Path(n).name=='libslang-llvm.so']; assert len(names)==1; Path('/tmp/libslang-llvm.so').write_bytes(z.read(names[0]))"

FROM ghcr.io/lilong555/repropatch-cross-cpp@sha256:7131796ef11523e09332f798cb50e5ce7a723d8da9d1e99a0927a83337588f4b
USER root
RUN apt-get update && apt-get install -y --no-install-recommends clang-14 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=llvm_input /tmp/libslang-llvm.so /opt/cpp-deps/slang-7815/libslang-llvm.so
USER 65534:65534
WORKDIR /build

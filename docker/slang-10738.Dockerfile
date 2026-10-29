FROM starryzhang/sweb.eval.x86_64.shader-slang_1776_slang-10738@sha256:9635af78e4149ca433ff9e8d1d056b1f08dba91a89b9e11c1151e065cf08ee2b AS official
FROM ghcr.io/lilong555/repropatch-cross-cpp@sha256:688d9f65c08c283a203d1ff03e7fc60f8b57167cfa925eaa26fb70d2d8b94533
USER root
RUN apt-get update && apt-get install -y --no-install-recommends clang-18 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=official /testbed/build/Release/lib/libslang-llvm.so /opt/cpp-deps/slang-10738/libslang-llvm.so
COPY --from=official /testbed/build/_deps/dxc-src /opt/cpp-deps/slang-10738/dxc
USER 65534:65534
WORKDIR /build

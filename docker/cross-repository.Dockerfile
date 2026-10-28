FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    clang-19 g++-11 g++-14 gcc g++ libc++-19-dev libc++abi-19-dev cmake ninja-build ccache python3 bash ripgrep ca-certificates \
    pkg-config re2c bison flex libgtest-dev libssl-dev libboost-all-dev libasio-dev libeigen3-dev \
    && rm -rf /var/lib/apt/lists/*
COPY .repropatch/cross-tools/ut /opt/cpp-deps/ut
COPY .repropatch/cross-tools/json-test-data /opt/json-test-data
COPY .repropatch/cross-tools/simdjson-data /opt/simdjson-data
COPY .repropatch/cross-tools/yaml-test-suite /opt/cpp-deps/yaml-test-suite
COPY .repropatch/cross-tools/libslang-llvm.so /opt/cpp-deps/libslang-llvm.so
COPY .repropatch/cross-tools/dependencies.json /opt/cpp-deps/dependencies.json
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUNBUFFERED=1
USER 65534:65534
WORKDIR /build

# 工具链基线对应固定 beb37 镜像，公开数据目录对应固定测试数据 commit。
FROM repropatch-json-base:beb37ec7c757
USER 0:0
COPY git-runtime/git /usr/bin/git
COPY git-runtime /usr/lib/git-core
COPY test-data /opt/json-test-data
COPY gitconfig /etc/gitconfig
RUN chmod -R a+rX /opt/json-test-data \
    && chmod 0644 /etc/gitconfig /usr/lib/git-core/copyright
LABEL org.repropatch.json-test-data-commit="a1375cea09d27cc1c4cadb8d00470375b421ac37"
USER 65534:65534
WORKDIR /build

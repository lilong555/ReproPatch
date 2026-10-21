# 构建前须确认本地 tag 的内容身份与 readiness.json 记录的上游镜像一致。
FROM mswebench/catchorg_m_catch2:pr-2723
USER root
# cmake 来自固定的 cmake==4.4.4 Python 分发中的 data 目录。
COPY cmake /opt/cmake
ENV PATH=/opt/cmake/bin:$PATH
RUN rm -rf /home/Catch2 /home/fix.patch /home/test.patch \
    /home/fix-run.sh /home/test-run.sh /home/run.sh /home/prepare.sh \
    /home/check_git_changes.sh
USER 65534:65534
WORKDIR /build

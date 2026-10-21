# 构建前须验证本地原始 tag 对应固定官方 image ID；保持 GCC 7.5.0 不变。
FROM mswebench/catchorg_m_catch2:pr-2187
USER root
# cmake 目录来自固定的 cmake==4.4.4 分发。
COPY cmake /opt/cmake
ENV PATH=/opt/cmake/bin:$PATH
RUN rm -rf /home/Catch2 /home/fix.patch /home/test.patch \
    /home/fix-run.sh /home/test-run.sh /home/run.sh /home/prepare.sh \
    /home/check_git_changes.sh \
    && if [ ! -e /usr/bin/sleep ]; then ln -s /bin/sleep /usr/bin/sleep; fi
USER 65534:65534
WORKDIR /build

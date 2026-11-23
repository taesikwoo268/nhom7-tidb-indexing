# TiKV v8.5.5 with the debug sections removed. The executable code is unchanged.
# The original binary keeps about 1.9 GB resident per node when idle (measured on
# M2, empty cluster). Without debug sections it keeps about 0.16 GB.
FROM pingcap/tikv:v8.5.5 AS source

FROM debian:bookworm-slim AS strip
RUN apt-get update \
    && apt-get install -y --no-install-recommends binutils \
    && rm -rf /var/lib/apt/lists/*
COPY --from=source /tikv-server /tikv-server
RUN strip --strip-debug /tikv-server

FROM pingcap/tikv:v8.5.5
COPY --from=strip /tikv-server /tikv-server

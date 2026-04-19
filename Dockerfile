FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DRISSION_KERNEL_BROWSER_PATH=/usr/bin/chromium

WORKDIR /workspace

RUN apt-get update \
 && apt-get install -y --no-install-recommends chromium \
 && rm -rf /var/lib/apt/lists/*

COPY . /workspace

RUN python -m pip install --upgrade pip \
 && python -m pip install --no-cache-dir -e .[test]

CMD ["sh", "-lc", "python tools/smoke/headless_browser_smoke.py && pytest -q"]

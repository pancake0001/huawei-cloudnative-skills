FROM aicli:beta-with-kubectl

COPY skills/ /root/.agents/skills/

COPY requirements.txt /tmp/requirements.txt
RUN pip3 config set global.index-url https://repo.huaweicloud.com/repository/pypi/simple \
    && pip3 config set install.trusted-host repo.huaweicloud.com \
    && pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && GITLEAKS_VERSION=8.25.1 \
    && curl -fsSL -o /tmp/gitleaks.tar.gz "https://gh-proxy.com/https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
    && tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks \
    && rm -f /tmp/gitleaks.tar.gz \
    && gitleaks version \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g markdownlint-cli2 \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root
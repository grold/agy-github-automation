# Dockerfile for Antigravity (agy) GitHub Actions Runner
FROM ubuntu:24.04

LABEL maintainer="Antigravity Automation"
LABEL description="Isolated container environment for Antigravity (agy) headless CI/CD execution"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV MISE_DATA_DIR=/opt/mise
ENV MISE_CONFIG_DIR=/etc/mise
ENV PATH="/opt/mise/shims:/opt/mise/bin:/usr/local/bin:${PATH}"

# Install core utilities, git, gh CLI, jq, curl, certificates, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    gnupg \
    jq \
    tar \
    gzip \
    unzip \
    build-essential \
    python3 \
    python3-dbus \
    python3-gi \
    python3-cryptography \
    sudo \
    dbus \
    dbus-x11 \
    libsecret-tools \
    python3-secretstorage \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI (gh)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install mise (tool manager) and install antigravity-cli
RUN curl https://mise.run | MISE_INSTALL_PATH=/usr/local/bin/mise sh \
    && mise use -g antigravity-cli@latest \
    && mise reshim

# Configure git safe directory
RUN git config --global --add safe.directory "*"

# Copy automation scripts and default agent prompts into the image
COPY .github/scripts /opt/agy-automation/scripts
COPY .github/agents /opt/agy-automation/agents
RUN chmod +x /opt/agy-automation/scripts/*.sh /opt/agy-automation/scripts/*.py
ENV PATH="/opt/agy-automation/scripts:${PATH}"

# Set workdir
WORKDIR /workspace

CMD ["/bin/bash"]

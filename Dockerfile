FROM python:3.12-slim

# Install Lambda Runtime Interface Client + system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg fonts-dejavu nodejs npm curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir awslambdaric

WORKDIR /var/task
ENV LAMBDA_TASK_ROOT=/var/task

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY main.py .
COPY steps/ steps/

# Claude auth is loaded at runtime from AWS Secrets Manager into /tmp
# (see _bootstrap_claude_auth in main.py — no credentials baked into image)

ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["main.lambda_handler"]

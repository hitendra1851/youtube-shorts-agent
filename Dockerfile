FROM public.ecr.aws/lambda/python:3.12

# Install ffmpeg + fonts + Node.js (required by Claude Code CLI)
RUN dnf install -y ffmpeg dejavu-sans-fonts nodejs && dnf clean all

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY main.py .
COPY steps/ steps/

# Mount ~/.claude/ auth at runtime via Lambda env or layer
# Set CLAUDE_CONFIG_DIR if auth files are stored elsewhere
ENV CLAUDE_CONFIG_DIR=/var/task/.claude

CMD ["main.lambda_handler"]

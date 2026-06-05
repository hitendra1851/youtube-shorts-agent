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

# Claude Code auth — deploy.sh copies ~/.claude/ here before docker build
# CLAUDE_CONFIG_DIR tells the Agent SDK where to find the auth token
COPY .claude/ /var/task/.claude/
ENV CLAUDE_CONFIG_DIR=/var/task/.claude

CMD ["main.lambda_handler"]

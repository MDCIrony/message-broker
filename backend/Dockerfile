FROM python:3.11-slim

# Copy the uv executable from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency definition
COPY pyproject.toml ./

# Install dependencies using system python via uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application files
COPY app/ app/

# Create a folder for the SQLite database
RUN mkdir -p /app/data
ENV DB_PATH=/app/data/broker.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

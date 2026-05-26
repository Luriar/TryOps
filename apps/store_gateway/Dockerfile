# Use ARM64 Debian-based Python image for Raspberry Pi compatibility
FROM python:3.11-slim-bookworm

# Install build dependencies for sqlcipher
RUN apt-get update && apt-get install -y \
    build-essential \
    sqlcipher \
    libsqlcipher-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install standard dependencies
COPY pyproject.toml .
RUN pip install --upgrade pip
RUN pip install hatchling
# Install pysqlcipher3 from source so it binds to the system's libsqlcipher
# We need to set compiler flags to tell it to use sqlcipher instead of sqlite3
RUN CFLAGS="-I/usr/include/sqlcipher" LDFLAGS="-L/usr/lib/aarch64-linux-gnu -lsqlcipher" \
    pip install pysqlcipher3

# Install the rest of the app dependencies
# We create a dummy src to allow pip install . to succeed on dependencies
RUN mkdir -p src/store_gateway && touch src/store_gateway/__init__.py
RUN pip install .

# Copy application source
COPY . .

# Re-install properly now that source is here
RUN pip install .

# Expose FastAPI HTTP Port
EXPOSE 5000

# Run FastAPI via uvicorn
CMD ["uvicorn", "store_gateway.main:app", "--host", "0.0.0.0", "--port", "5000"]

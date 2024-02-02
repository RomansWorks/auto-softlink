# Use the Alpine Python image as the base image
FROM python:3.12-bookworm as builder

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1
RUN pip install --no-cache-dir poetry

# Set the working directory inside the container
WORKDIR /app

# Copy the poetry.lock and pyproject.toml files into the container
COPY poetry.lock pyproject.toml /app/
# Install the required dependencies
RUN poetry install --no-root --no-dev

# Runtime image
FROM python:3.12-slim-bookworm as runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Copy the installed dependencies from the builder image
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Copy the rest of the source code into the container
COPY . /app

WORKDIR /app



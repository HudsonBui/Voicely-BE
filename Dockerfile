FROM python:3.12-bookworm
LABEL maintainer="Dan Bui"

ENV PYTHONUNBUFFERED=1

COPY ./requirements.txt /tmp/requirements.txt
COPY ./app /app
WORKDIR /app
EXPOSE 8000

RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install -r /tmp/requirements.txt && \
    rm -rf /tmp/requirements.txt

# Setup user
RUN adduser \
    --disabled-password \
    --no-create-home \
    voicely-user && \
    mkdir -p /vol/web/media && \
    mkdir -p /vol/web/static && \
    chown -R voicely-user:voicely-user /vol && \
    chmod -R 755 /vol

ENV PATH="/py/bin:$PATH"

USER voicely-user

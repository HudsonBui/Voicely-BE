# 1. Dùng base image "slim" để image nhẹ hơn
FROM python:3.12-slim-bookworm
LABEL maintainer="Dan Bui"

ENV PYTHONUNBUFFERED=1

# Thiết lập venv và PATH ngay từ đầu
ENV VIRTUAL_ENV=/py
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Cài đặt các gói hệ thống (ffmpeg) trước
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Cài đặt Python (tạo venv)
RUN python -m venv $VIRTUAL_ENV && \
    pip install --upgrade pip

WORKDIR /code

# 2. Tối ưu caching: Chỉ copy requirements.txt và install
# Layer này sẽ được cache, chỉ chạy lại khi requirements.txt thay đổi
COPY ./requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && \
    rm -rf /tmp/requirements.txt

# 3. Copy code ứng dụng SAU KHI đã install
# Thay đổi code ở đây sẽ không làm chạy lại pip install
COPY ./app /code/app
COPY ./alembic.ini /code/alembic.ini
COPY ./alembic /code/alembic

# Cài đặt user và quyền (Giữ nguyên, rất tốt!)
RUN addgroup --gid 1000 voicely-user && \
    adduser \
    --disabled-password \
    --no-create-home \
    --uid 1000 \
    --gid 1000 \
    voicely-user && \
    mkdir -p /vol/web/media && \
    mkdir -p /vol/web/static && \
    mkdir -p /code/uploads/audio && \
    chown -R voicely-user:voicely-user /vol && \
    chown -R voicely-user:voicely-user /code/uploads && \
    chmod -R 755 /vol && \
    chmod -R 755 /code/uploads

USER voicely-user

# 4. Xóa `EXPOSE 8000` (không cần thiết cho Cloud Run)

# 5. Sửa CMD sang "shell form" để $PORT hoạt động
CMD uvicorn app.main:sio_app --host 0.0.0.0 --port $PORT

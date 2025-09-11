FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-dev \
    libffi-dev \
    shared-mime-info \
    fontconfig \
    fonts-dejavu-core \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fonts-ipafont-gothic \
    fonts-ipafont-mincho \
    fonts-noto-color-emoji \
    && fc-cache -f -v \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install uv
# Install app with dev extras so we can run tests in-container
RUN uv pip install --system '.[dev]'

RUN mkdir -p uploads output

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

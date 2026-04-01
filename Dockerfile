FROM python:3.12-slim

WORKDIR /app

COPY main.py /app/main.py

# Tkinter для python:3.12-slim устанавливается через python3-tk
RUN apt-get update && apt-get install -y --no-install-recommends python3-tk \
    && rm -rf /var/lib/apt/lists/*

CMD ["python", "main.py"]

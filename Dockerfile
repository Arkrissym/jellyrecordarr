FROM python:3-slim

COPY requirements.txt /requirements.txt
COPY src/ /app/

RUN pip install -r /requirements.txt

WORKDIR /app
ENTRYPOINT [ "python", "-u", "main.py" ]

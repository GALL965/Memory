FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
RUN chmod +x /app/scripts/gen_proto.sh && /app/scripts/gen_proto.sh

CMD ["python", "clients/console/main.py", "--host", "server", "--port", "50051", "--name", "Player"]

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN chmod +x /app/scripts/gen_proto.sh && /app/scripts/gen_proto.sh

EXPOSE 50051

CMD ["python", "server/main.py"]

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY gateway/requirements.txt /app/gateway/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt -r /app/gateway/requirements.txt

COPY . /app

RUN python -m grpc_tools.protoc \
  -I /app/proto \
  --python_out=/app/shared/grpc \
  --grpc_python_out=/app/shared/grpc \
  /app/proto/memory.proto \
  && sed -i 's/^import memory_pb2 as memory__pb2$/from . import memory_pb2 as memory__pb2/' /app/shared/grpc/memory_pb2_grpc.py

EXPOSE 8000

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]

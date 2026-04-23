FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
RUN python -m grpc_tools.protoc \
  -I /app/proto \
  --python_out=/app/shared/grpc \
  --grpc_python_out=/app/shared/grpc \
  /app/proto/memory.proto \
  && sed -i 's/^import memory_pb2 as memory__pb2$/from . import memory_pb2 as memory__pb2/' /app/shared/grpc/memory_pb2_grpc.py

CMD ["python", "clients/console/main.py", "--host", "server", "--port", "50051", "--name", "Player"]

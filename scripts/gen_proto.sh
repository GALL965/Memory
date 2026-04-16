#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="$ROOT_DIR/proto"
OUT_DIR="$ROOT_DIR/shared/grpc"

python3 -m grpc_tools.protoc \
  -I "$PROTO_DIR" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  "$PROTO_DIR/memory.proto"

# grpcio-tools generates absolute imports (import memory_pb2) even inside packages.
# Fix to a relative import so `from shared.grpc import memory_pb2_grpc` works.
sed -i 's/^import memory_pb2 as memory__pb2$/from . import memory_pb2 as memory__pb2/' "$OUT_DIR/memory_pb2_grpc.py"

echo "Generated gRPC stubs into $OUT_DIR"

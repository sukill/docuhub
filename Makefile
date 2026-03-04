.PHONY: proto api storagenode

proto:
	mkdir -p ./docuhub/generated
	touch ./docuhub/generated/__init__.py
	uv run python -m grpc_tools.protoc \
		-I./proto \
		--python_out=./docuhub/generated \
		--grpc_python_out=./docuhub/generated \
		./proto/repository.proto
	@# Fix absolute import to relative import for package compatibility
	@if [ "$$(uname)" = "Darwin" ]; then \
		sed -i '' 's/import repository_pb2/from . import repository_pb2/' ./docuhub/generated/repository_pb2_grpc.py; \
	else \
		sed -i 's/import repository_pb2/from . import repository_pb2/' ./docuhub/generated/repository_pb2_grpc.py; \
	fi
	@echo "Protobuf generated and patched successfully."

api:
	uv run python main.py api --reload

storagenode:
	uv run python main.py storagenode

import argparse
import sys
import uvicorn
import os


def run_api(args):
    print(f"Starting API Server on {args.host}:{args.port}...")
    uvicorn.run(
        "docuhub.api.main:app", host=args.host, port=args.port, reload=args.reload
    )


def run_storagenode(args):
    print("Starting Storage Node...")
    # Import inside function to avoid heavy imports if only running API
    from docuhub.storagenode.service import serve

    # Set environment variables if provided in args
    if args.port:
        os.environ["STORAGE_PORT"] = str(args.port)
    if args.node_id:
        os.environ["NODE_ID"] = args.node_id

    serve()


def main():
    parser = argparse.ArgumentParser(
        description="DocuHub: Distributed Git-based Guideline Repository System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # API Server parser
    api_parser = subparsers.add_parser("api", help="Run the API Server")
    api_parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)"
    )
    api_parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind (default: 8000)"
    )
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # Storage Node parser
    node_parser = subparsers.add_parser("storagenode", help="Run the Storage Node")
    node_parser.add_argument("--port", type=int, help="gRPC port for the node")
    node_parser.add_argument("--node-id", help="Node ID for the node")

    args = parser.parse_args()

    if args.command == "api":
        run_api(args)
    elif args.command == "storagenode":
        run_storagenode(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

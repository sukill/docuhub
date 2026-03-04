import redis
import grpc
import hashlib
import json

# Placeholder for gRPC stubs
# In a real environment, these would be:
# import repository_pb2
# import repository_pb2_grpc

class RepositoryRouter:
    def __init__(self, redis_host='localhost', redis_port=6379, db=0):
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=db, decode_responses=True)
        self.node_clients = {} # node_id -> gRPC client
        self.node_registry = {} # node_id -> address (e.g. "10.0.0.1:50051")

    def register_node(self, node_id, address):
        """Register or update a storage node's address."""
        self.redis.hset("storage_nodes", node_id, address)
        self.node_registry[node_id] = address

    def get_node_for_user(self, user_id):
        """
        Get the assigned storage node for a user.
        If not assigned, assign one based on simple hashing/round-robin.
        """
        node_id = self.redis.get(f"user_node:{user_id}")
        if not node_id:
            # Simple consistent hashing or assignment logic
            nodes = self.list_active_nodes()
            if not nodes:
                raise Exception("No active storage nodes available")
            
            # Use user_id hash to pick a node
            hash_val = int(hashlib.sha256(user_id.encode()).hexdigest(), 16)
            node_id = nodes[hash_val % len(nodes)]
            
            # Store the mapping
            self.redis.set(f"user_node:{user_id}", node_id)
            
        return node_id

    def list_active_nodes(self):
        """List all registered storage nodes."""
        nodes = self.redis.hkeys("storage_nodes")
        return nodes

    def get_client_stub(self, user_id):
        """Get a gRPC client stub for the node assigned to the user."""
        node_id = self.get_node_for_user(user_id)
        
        if node_id not in self.node_clients:
            address = self.redis.hget("storage_nodes", node_id)
            if not address:
                raise Exception(f"Node {node_id} address not found in registry")
            
            channel = grpc.insecure_channel(address)
            # In a real setup:
            # self.node_clients[node_id] = repository_pb2_grpc.RepositoryServiceStub(channel)
            # For now, return a placeholder or the channel itself to show logic
            self.node_clients[node_id] = repository_pb2_grpc.RepositoryServiceStub(channel)
            
        return self.node_clients[node_id]

    def clear_cache(self, user_id):
        """Clear the cached routing for a user (e.g. during migration)."""
        self.redis.delete(f"user_node:{user_id}")

import os
import weaviate
from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, FilterOperator

class RagEngine:
    def __init__(self):
        self.weaviate_url = os.getenv("WEAVIATE_URL")
        self.global_index = None

        if self.weaviate_url:
            self._connect_weaviate()
        else:
            print("RAG: WEAVIATE_URL not set. RAG features disabled.", flush=True)

    def _connect_weaviate(self):
        try:
            print(f"Connecting to Weaviate at {self.weaviate_url}...", flush=True)
            # Assuming localhost/network alias 'weaviate' based on docker-compose
            # The URL provided is http://weaviate:8080 usually. 
            # The original code hardcoded host parameters in connect_to_custom.
            # We will preserve that logic but wrap it safely.
            
            client = weaviate.connect_to_custom(
                http_host="weaviate",      
                http_port=8080,
                http_secure=False,         
                grpc_host="weaviate",      
                grpc_port=50051,           
                grpc_secure=False,
            )
            
            vector_store = WeaviateVectorStore(weaviate_client=client, index_name="PermanentKnowledge")
            self.global_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
            print("RAG: Weaviate connected and index loaded.", flush=True)
        except Exception as e:
            print(f"RAG Error: Could not connect to Weaviate. {e}", flush=True)
            self.global_index = None

    def process_request(self, question, auth_params):
        if not self.global_index:
            return "Error: RAG is disabled or unavailable."

        if isinstance(auth_params, str):
            auth_params = [auth_params]
        
        if not auth_params:
            return "Error: Access Denied (No Auth Params)."

        acl_filters = []
        for param in auth_params:
            acl_filters.append(MetadataFilter(
                key="access_level",
                value=param,
                operator=FilterOperator.EQ
            ))

        if len(acl_filters) > 1:
            secure_filters = MetadataFilters(filters=acl_filters, condition="or")
        else:
            secure_filters = MetadataFilters(filters=acl_filters)

        query_engine = self.global_index.as_query_engine(
            filters=secure_filters,
            similarity_top_k=3
        )

        response = query_engine.query(question)
        return str(response)

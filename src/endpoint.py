from api_requester import APIRequester
from langchain_core.tools import tool
from llm_utils import execute_api_request, generate_api_request
import requests
from langchain.embeddings import OllamaEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams
import yaml
import logging
logger = logging.getLogger(__name__)

embeddings = OllamaEmbeddings(model="llama3.2", base_url="http://localhost:11434")
 # Initialize Qdrant client with online host and optional token
qdrant = QdrantClient(
    url="https://505ad89f-e404-469f-b783-a41f3e7b2b60.europe-west3-0.gcp.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwiZXhwIjoxNzQ3NzgyMDE0fQ.WxZgOxrOoc2LsOSZPbJHznmHkeob6q8_m283qY_-7nk",
)

QDRANT_COLLECTION = "openapi_endpoints3"

def extract_endpoints_from_openapi(spec_content):
    """Extract endpoints from a loaded OpenAPI spec (as dict)."""
    endpoints = []
    paths = spec_content.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            endpoint = {
                "path": path,
                "method": method.upper(),
                "summary": details.get("summary", ""),
                "description": details.get("description", ""),
                "operationId": details.get("operationId", ""),
                "responses": details.get("responses", {})
            }
            # Combine summary and description as text for embedding
            endpoint["text"] = f"{endpoint['summary']} {endpoint['description']}".strip()
            endpoints.append(endpoint)
    return endpoints

def get_embedding(text: str) -> list:
    return embeddings.embed_query(text)

def index_endpoints_from_url(spec_url):
    """
    Fetch the OpenAPI spec from a URL, extract endpoints, and upsert them into Qdrant.
    Run this once to index your spec.
    """
    response = requests.get(spec_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch spec from URL: {spec_url}")
    spec = yaml.safe_load(response.text)
    endpoints = extract_endpoints_from_openapi(spec)
    point_id = 1
    points = []
    for ep in endpoints:
        text_for_embedding = ep["text"] if ep["text"] else f"{ep['path']} {ep['method']}"
        embedding = get_embedding(text_for_embedding)
        metadata = {
            "path": ep["path"],
            "method": ep["method"],
            "operationId": ep["operationId"],
            "summary": ep["summary"],
            "description": ep["description"],
            "responses": ep["responses"]
        }
        points.append(PointStruct(id=point_id, vector=embedding, payload=metadata))
        point_id += 1
    if points:
        qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"Indexed {len(points)} endpoints from spec at {spec_url}.")


# Ensure the collection exists (create if necessary)
try:
    qdrant.get_collection(collection_name=QDRANT_COLLECTION)
except Exception:
    qdrant.recreate_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=3072, distance="Cosine")
    )
    index_endpoints_from_url("http://localhost:8000/openapi.json")


@tool
def get_apidoc(user_query: str) -> str:
    """Tool search for matching endpoint from vector store, prepare the request, and execute the request, and return formatted response.""" 
    query_vector = get_embedding(user_query)
    search_result = qdrant.search(
    collection_name=QDRANT_COLLECTION,
        query_vector=query_vector,
            limit=1
        )
    if not search_result:
        return "No relevant information found."
    endpoint = search_result[0].payload
    logger.debug(f"found the metadata {endpoint}")
    api_requester = APIRequester()
    api_request = generate_api_request(user_query, endpoint)

    if not api_request:
        return "Failed to generate API request."

    api_response = execute_api_request(api_request, api_requester)
    return api_response



from api_requester import APIRequester
from langchain_core.tools import tool
from typing_extensions import TypedDict
from typing import Literal, Annotated
from llm_utils import execute_api_request, generate_api_request
import requests_cache
import pandas as pd
from retry_requests import retry
from langchain.embeddings import OllamaEmbeddings

import logging

from vector_search import create_vector_database
logger = logging.getLogger(__name__)
embeddings = OllamaEmbeddings(model="llama3.2", base_url="http://localhost:11434")

# Setup the Open-Meteo API client with cache and retry on error
 
@tool
def get_apidoc(user_query: str) -> str:
    """Tool search for matching endpoint from vector store, prepate the request, and execute the request, and return formatted response.""" 
    vectorstore = create_vector_database()
    print({user_query})
    results = vectorstore.similarity_search(user_query, k=1)  # Correct variable name
    if not results:
        return "No relevant information found."
    endpoint = results[0].metadata
    print(f"found the metadata {endpoint}")
    api_requester = APIRequester()
    api_request = generate_api_request(user_query, endpoint)
    print(f"found the metadata {api_request}")

    if not api_request:
            return "Failed to generate API request."

        # Step 3: Execute the API request
    api_response = execute_api_request(api_request, api_requester)
    return api_response


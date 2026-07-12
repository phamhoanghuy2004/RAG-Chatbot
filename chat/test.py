from qdrant_client import QdrantClient
from qdrant_client.http.models import PayloadSchemaType

client = QdrantClient(
    url="https://86cf8d40-9d4c-4784-b991-a9e83f566cfe.us-east-1-1.aws.cloud.qdrant.io:6333",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6NTdhZjc3N2EtNjM4Yy00MDg2LWEyMmMtNjYwYjhiMTFhMjY5In0.ppAzie9nySmpGzpX4jj5BMa1zKTmxAnaALCZtLazpUk"
)

client.create_payload_index(
    collection_name="knowledge_base",
    field_name="metadata.source",
    field_schema=PayloadSchemaType.KEYWORD
)
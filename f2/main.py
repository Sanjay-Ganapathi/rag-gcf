import functions_framework
import os
from dotenv import load_dotenv
from google.cloud import storage
import tempfile

from llama_index.embeddings.langchain import LangchainEmbedding
from langchain_openai import AzureOpenAIEmbeddings
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core import Settings


load_dotenv()

storage_client = storage.Client()


@functions_framework.http
def query_with_docs(request):

    if request.method != 'POST':
        return 'Only POST requests are accepted', 405

    embeddings = AzureOpenAIEmbeddings(
        api_key=os.getenv('EMBEDDINGS_AZURE_OPENAI_APIKEY'),
        api_version=os.getenv('EMBEDDINGS_AZURE_OPENAI_API_VERSION'),
        azure_endpoint=os.getenv('EMBEDDINGS_AZURE_OPENAI_ENDPOINT'),
        model=os.getenv('EMBEDDINGS_AZURE_OPENAI_EMBED_MODEL'),
        azure_deployment="embeddings"
    )

    embed_model = LangchainEmbedding(embeddings)

    llm = AzureOpenAI(
        engine=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        model="gpt-4-32k",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_APIKEY"),
        api_version="2024-02-15-preview",

    )

    Settings.llm = llm
    Settings.embed_model = embed_model

    request_data = request.get_json()

    question = request_data.get('question')
    file_names = request_data.get('files')

    if not question:
        return 'No question provided', 400

    bucket_name = os.getenv('BUCKET_NAME')
    bucket = storage_client.bucket(bucket_name)

    with tempfile.TemporaryDirectory() as temp_dir:
        if not file_names:

            blobs = list(bucket.list_blobs())

            for blob in blobs:
                local_path = os.path.join(temp_dir, blob.name)
                blob.download_to_filename(local_path)

        else:
            for file_name in file_names:
                blob = bucket.blob(file_name)
                if blob.exists():
                    local_path = os.path.join(temp_dir, file_name)
                    blob.download_to_filename(local_path)
                else:
                    return f'File {file_name} not found in bucket {bucket_name}', 400

        docs = SimpleDirectoryReader(
            temp_dir, num_files_limit=10).load_data(num_workers=4)

        index = VectorStoreIndex.from_documents(docs, embed_model=embed_model)
        query_engine = index.as_query_engine()
        response = query_engine.query(question)
        return response.response

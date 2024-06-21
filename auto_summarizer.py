
import os
import re
import requests
import logging
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from ratelimit import limits, sleep_and_retry
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import TextLoader

# Set up logging to both stdout and a file
log_file = "app.log"
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout),
                              logging.FileHandler(log_file)])

# Set the embedding model and LLM settings
Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
Settings.llm = Ollama(model="mistral", request_timeout=360.0)

PERSIST_DIR = "./storage"
DATA_DIR = "./data"

# Rate limit the indexing process to 1 call per 5 seconds
@sleep_and_retry
@limits(calls=1, period=5)
def index_documents():
    # Load the documents from the specified directory using SimpleDirectoryReader
    documents = SimpleDirectoryReader(DATA_DIR).load_data()
    # Create the index from the loaded documents
    index = VectorStoreIndex.from_documents(documents)
    # Persist the storage context for later use
    index.storage_context.persist(persist_dir=PERSIST_DIR)
    return index

# Ensure the persistence and data directories exist
if not os.path.exists(PERSIST_DIR):
    os.makedirs(PERSIST_DIR)

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Function to fetch YouTube video title
def get_youtube_video_title(video_url):
    response = requests.get(video_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find("meta", property="og:title")
        if title_tag:
            return title_tag["content"]
        else:
            raise Exception("Video title not found")
    else:
        raise Exception("Failed to fetch the YouTube page")

# Function to download YouTube transcript
def download_youtube_transcript(video_url):
    try:
        # Extract video ID from URL
        video_id_match = re.search(r"v=([a-zA-Z0-9_-]{11})", video_url)
        if not video_id_match:
            raise ValueError("Invalid YouTube URL")

        video_id = video_id_match.group(1)

        # Fetch the video title
        title = get_youtube_video_title(video_url)

        # Fetching the transcript
        srt = YouTubeTranscriptApi.get_transcript(video_id)

        # Replacing invalid characters in filenames
        valid_title = re.sub(r'[\\/*?:"<>|]', "", title)

        # Writing the transcript to a file named after the video title in the data folder
        transcript_file = os.path.join(DATA_DIR, f"{valid_title}.txt")
        with open(transcript_file, "w", encoding='utf-8') as f:
            for item in srt:
                f.write(f"{item['text']}\n")
        print("Transcript downloaded successfully.")
        return transcript_file
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Load all .txt files from the specified directory
def load_txt_documents(directory_path):
    docs = []
    for txt_file in Path(directory_path).glob('*.txt'):
        docs.extend(TextLoader(txt_file).load())
    return docs

# Split the loaded documents
def split_documents(docs):
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    return text_splitter.split_documents(docs)

# Main execution
if __name__ == "__main__":
    video_url = input("Enter the YouTube Video URL: ")
    transcript_file = download_youtube_transcript(video_url)

    if transcript_file:
        with open(transcript_file, "r", encoding='utf-8') as f:
            transcript_text = f.read()

        # Load and split documents from 'data' directory
        docs = load_txt_documents(DATA_DIR)
        documents = split_documents(docs)

        # Index the documents
        index = index_documents()

        # Summarize the transcript text using the query engine
        query_str = """
        Please summarize the following transcript:

        {transcript_text}

        The summary should highlight the key points, main topics discussed, and any important conclusions or recommendations made in the transcript.
        """

        query_engine = index.as_query_engine(similarity_top_k=2)
        vector_retriever = index.as_retriever(similarity_top_k=2)

        # Execute the query and print the response
        response = query_engine.query(query_str.format(transcript_text=transcript_text))
        print(str(response))

        # Print a message indicating that the process is complete
        print("Process completed successfully.")

import os
import re
import requests
import logging
import sys
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from ratelimit import limits, sleep_and_retry
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import TextLoader
import shutil
import time

# Set up logging to both stdout and a file
log_file = "app.log"
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout),
                              logging.FileHandler(log_file)])

# Set the embedding model and LLM settings
Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
Settings.llm = Ollama(model="llama3", request_timeout=360.0)

PERSIST_DIR = "./storage"
DATA_DIR = "./data"
SUMMARIES_DIR = "./summaries"

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

# Ensure the persistence, data, and summaries directories exist
for directory in [PERSIST_DIR, DATA_DIR, SUMMARIES_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

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
        logging.info("Transcript downloaded successfully.")
        return transcript_file
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return None

# Load all .txt files from the specified directory
def load_txt_documents(directory_path):
    docs = []
    for txt_file in Path(directory_path).glob('*.txt'):
        docs.extend(TextLoader(txt_file).load())
    return docs

# Split the loaded documents
def split_documents(docs):
    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    return text_splitter.split_documents(docs)

# Delete all files in a given directory
def delete_files_in_directory(directory_path):
    for file in Path(directory_path).glob('*'):
        try:
            if file.is_file() or file.is_symlink():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)
        except Exception as e:
            logging.error(f'Failed to delete {file}. Reason: {e}')

# Function to split text into chunks
def split_text_into_chunks(text, chunk_size=500):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# Check if a directory is empty
def is_directory_empty(directory_path):
    return not any(Path(directory_path).iterdir())

# Function to read URLs from a text file
def read_urls_from_file(file_path):
    with open(file_path, "r") as file:
        urls = [line.strip() for line in file if line.strip()]
    return urls

def combine_and_deduplicate_summaries(summaries):
    seen = set()
    combined_summary = []
    for summary in summaries:
        if summary not in seen:
            seen.add(summary)
            combined_summary.append(summary)
    return "\n".join(combined_summary)

# Main execution
if __name__ == "__main__":
    urls_file = "E:\\AI Projects\\LlamaIndex RAG\\Youtube Transcript Summarizer\\urls.txt"  # Define the file containing YouTube video URLs directly

    start_time = time.time()

    # Ask if the user wants to delete files in the data and storage directories at the beginning
    if not is_directory_empty(DATA_DIR) or not is_directory_empty(PERSIST_DIR):
        delete_confirmation = input("Do you want to delete all files in the data and storage directories? (yes/no): ")
        if delete_confirmation.lower() == 'yes':
            delete_files_in_directory(DATA_DIR)
            delete_files_in_directory(PERSIST_DIR)

    # Check if data and storage directories are not empty and log the status
    if is_directory_empty(DATA_DIR):
        logging.info(f"The data directory '{DATA_DIR}' is empty.")
    else:
        logging.info(f"The data directory '{DATA_DIR}' is not empty.")

    if is_directory_empty(PERSIST_DIR):
        logging.info(f"The storage directory '{PERSIST_DIR}' is empty.")
    else:
        logging.info(f"The storage directory '{PERSIST_DIR}' is not empty.")

    urls = read_urls_from_file(urls_file)
    for video_url in urls:
        transcript_file = download_youtube_transcript(video_url)

        if transcript_file:
            with open(transcript_file, "r", encoding='utf-8') as f:
                transcript_text = f.read()

            # Load and split documents from 'data' directory
            docs = load_txt_documents(DATA_DIR)
            documents = split_documents(docs)

            # Index the documents
            index = index_documents()
            logging.info("Indexing completed successfully.")

            # Summarize the transcript text using the query engine
            query_str = """
            Please provide a detailed summary of the following chemistry content, formatted as bullet points. Each bullet point should consist of a couple of sentences, highlighting:

            - Key points
            - Main topics discussed
            - Important concepts explained
            - Experimental methods described
            - Significant conclusions or recommendations made

            {transcript_text}

            The summary should be objective and directly address the content without referring to it as a transcript.
            """

            query_engine = index.as_query_engine(similarity_top_k=1)

            # Split the transcript text into manageable chunks
            transcript_chunks = split_text_into_chunks(transcript_text)

            # Summarize each chunk and combine the summaries
            chunk_summaries = []
            for chunk in transcript_chunks:
                response = query_engine.query(query_str.format(transcript_text=chunk))
                logging.debug(f"Chunk response: {response}")
                chunk_summaries.append(str(response))

            # Combine and deduplicate summaries
            full_summary = combine_and_deduplicate_summaries(chunk_summaries)

            summary_file_path = os.path.join(SUMMARIES_DIR, f"{Path(transcript_file).stem}_summary.txt")
            with open(summary_file_path, "w", encoding='utf-8') as summary_file:
                summary_file.write(full_summary)
                logging.info(f"Summary written to {summary_file_path}")
                print(full_summary)

            # Delete files in the storage directory after summarization
            delete_files_in_directory(PERSIST_DIR)

    # Print a message indicating that the process is complete
    logging.info("Process completed successfully.")
    print("\nProcess completed successfully.")

    end_time = time.time()
    total_duration = end_time - start_time
    logging.info(f"Total time taken: {total_duration:.2f} seconds")
    print(f"Total time taken: {total_duration:.2f} seconds")

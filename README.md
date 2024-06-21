# YouTube Transcript Summarizer

This project enables you to download transcripts from YouTube videos and summarize the content using a language model.

## Features

- Download YouTube video transcripts.
- Save transcripts to a specified directory.
- Index documents for efficient querying.
- Summarize transcript content using a language model.
- Option to clear data and storage folders, ensuring a fresh run each time.

## Requirements

- Python 3.7+
- Install the required Python libraries using `pip`:

```bash
pip install -r requirements.txt
```

## Usage

1. Clone the repository and navigate to the project directory.

2. Create a `requirements.txt` file with the following content or use the provided one:

```plaintext
beautifulsoup4==4.9.3
requests==2.25.1
youtube-transcript-api==0.4.4
ratelimit==2.2.1
pathlib2==2.3.5
logging==0.4.9.6
llama-index==0.1.0
langchain==0.2.2
```

3. Install the dependencies:

```bash
pip install -r requirements.txt
```

4. Run the script:

```bash
python auto_summarize.py
```

5. Follow the prompts to enter a YouTube video URL. The transcript will be downloaded, saved, indexed, and summarized. You will also be asked if you want to clear the data and storage folders before proceeding.

## Script Overview

The script performs the following tasks:

1. Sets up logging.
2. Configures the embedding model and language model settings.
3. Defines a rate-limited function to index documents.
4. Ensures the persistence and data directories exist.
5. Defines functions to fetch YouTube video titles and download transcripts.
6. Loads and splits documents from the specified directory.
7. Prompts the user for a YouTube video URL, downloads the transcript, saves it to the data directory, and indexes the documents.
8. Prompts the user to confirm clearing of data and storage folders.
9. Summarizes the transcript content using the query engine and streams the response.

## Example

```python
Enter the YouTube Video URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
Do you want to clear the data and storage folders? (yes/no): yes
Transcript downloaded successfully.
Please summarize the following transcript:
[Transcript text]
The summary should highlight the key points, main topics discussed, and any important conclusions or recommendations made in the transcript.
[Streamed summary output]
Process completed successfully.
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements

- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)
- [YouTube Transcript API](https://pypi.org/project/youtube-transcript-api/)
- [RateLimit](https://pypi.org/project/ratelimit/)
- [LangChain](https://langchain.com/)
- [Llama Index](https://llamaindex.com/)

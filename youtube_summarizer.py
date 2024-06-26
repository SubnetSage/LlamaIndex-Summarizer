import requests
import re
from youtube_transcript_api import YouTubeTranscriptApi

# Function to make an API call
def make_api_call(prompt):
    url = http://OLLAMAURL/api/generate'
    payload = {
        'model': 'llama3',
        'prompt': prompt,
        'stream': False  # Set stream to True if real-time response is needed
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()['response']
    else:
        print(f"API call failed with status code {response.status_code}: {response.text}")
        return None

# Function to fetch and parse the YouTube video title for naming the transcript file
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
        raise Exception(f"Failed to fetch YouTube page with status code {response.status_code}")

# Function to download the YouTube transcript
def download_youtube_transcript(video_url):
    try:
        video_id = video_url.split("v=")[-1][:11]  # Extract video ID from URL
        srt = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = ' '.join([item['text'] for item in srt])
        return transcript_text
    except Exception as e:
        print(f"An error occurred while downloading transcript: {e}")
        return None

def main():
    video_url = input("Enter YouTube video URL: ")
    transcript_text = download_youtube_transcript(video_url)

    if transcript_text:
        print("\nOriginal Transcript:\n", transcript_text)
        prompt = "Summarize the main topics and key details discussed in the video, highlighting significant points: " + transcript_text
        summary = make_api_call(prompt)
        if summary:
            print("\nSummary:\n", summary)
        else:
            print("Failed to summarize the transcript.")
    else:
        print("No transcript available for this video.")

if __name__ == "__main__":
    main()

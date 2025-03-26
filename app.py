import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai
import os
import re  # Import the regular expression module


def get_youtube_video_id(url):
    """
    Extracts the video ID from a YouTube URL. Handles various URL formats,
    including edge cases and error conditions.

    Args:
        url: The YouTube video URL.

    Returns:
        The video ID as a string, or None if the URL is invalid or the ID
        cannot be extracted.
    """
    try:
        if not url:  # Handle empty or None URL
            return None

        url = url.strip()  # Remove leading/trailing whitespace

        # Handle youtu.be URLs
        if "youtu.be" in url:
            parsed_url = urlparse(url)
            video_id = parsed_url.path[1:]  # Remove the leading '/'
            if not video_id:
                return None  # Handle cases like "youtu.be/"
            return video_id

        # Handle youtube.com URLs
        if "youtube.com" in url:
            parsed_url = urlparse(url)

            # Handle /watch?v=...
            if parsed_url.path == "/watch":
                query_params = parse_qs(parsed_url.query)
                if 'v' in query_params:
                    video_id = query_params['v'][0]
                    if video_id: #check if its empty
                        return video_id
                    else: return None
                else: return None


            # Handle /shorts/...
            elif parsed_url.path.startswith("/shorts/"):
                video_id = parsed_url.path.split('/')[-1]
                if video_id:
                    return video_id
                else: return None

            # Handle /embed/...
            elif parsed_url.path.startswith("/embed/"):
                video_id = parsed_url.path.split('/')[-1]
                if video_id: return video_id
                else: return None

            # Handle /v/... (old-style URLs)
            elif parsed_url.path.startswith("/v/"):
                video_id = parsed_url.path.split('/')[-1]
                if video_id: return video_id
                else: return None
            
            # Handle URLs with timestamps (&t=...)
            # Remove timestamp before parsing by finding the index of "&t="
            t_index = url.find("&t=")
            if t_index != -1:
                url = url[:t_index]  # Keep only the part before &t=

             # Handle mobile links (m.youtube.com)
            if "m.youtube.com" in url:
                url = url.replace("m.youtube.com", "youtube.com")  # Convert to regular URL
                return get_youtube_video_id(url) # Recursive call
            
            # Handle /live/ urls
            elif parsed_url.path.startswith("/live/"):
                video_id = parsed_url.path.split('/')[-1]
                if video_id: return video_id
                else: return None

            else:
                return None  # Unsupported path

        return None  # Not a YouTube URL

    except Exception as e:
        print(f"Error parsing URL: {e}")  # Log the error for debugging
        return None

def get_youtube_transcript_text(video_id):
    """Retrieves the plain text transcript."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(['ml'])
        except:
            try:
                transcript = transcript_list.find_generated_transcript(['ml'])
            except Exception:
                st.error("No Malayalam transcript found.")
                return None
        transcript_data = transcript.fetch()
        text_only = " ".join(segment['text'] for segment in transcript_data)
        return text_only.strip()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

def generate_tags_with_gemini(transcript, api_key, num_tags=10):  # Add api_key parameter
    """Generates tags using the Gemini API."""
    if not api_key:
        st.error("Missing Gemini API key. Please enter your Gemini API key.")
        return None
    if not transcript:
        return None  # Handle empty transcript case

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (f"Generate a maximum of {num_tags} relevant tags for this Malayalam video transcript. "
                  "Provide only the tags, separated by commas. No other text. No numbers. Plain text, NOT JSON. No hashtags. "
                  f"Transcript:\n{transcript}\nTags:")
        response = model.generate_content(prompt)
        tags_string = response.text
        tags = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
        return tags

    except Exception as e:
        st.error(f"Error generating tags: {e}")
        return None

# --- Streamlit App ---
st.title("YouTube Malayalam Transcript & Tag Extractor (Gemini)")

# Custom CSS for tag cloud layout
st.markdown("""
<style>
.tag-cloud {
    display: flex;
    flex-wrap: wrap; /* Allow tags to wrap to the next line */
    gap: 5px; /* Spacing between tags */
}
.tag {
    background-color: #f0f2f6; /* Light gray background */
    color: #0e1117; /* Dark text color */
    padding: 5px 10px;
    border-radius: 5px;
    border: 1px solid #d1d5db; /* Light gray border */
    font-size: 0.9em;
    display: inline-block; /* Important for wrapping */
     /* Remove button-like appearance */
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;

}
</style>
""", unsafe_allow_html=True)


# Get API key from user input
api_key = st.text_input("Enter your Gemini API key:", type="password")

url = st.text_input("Enter YouTube Video URL:")

if url:
    video_id = get_youtube_video_id(url)
    if video_id:
        with st.spinner("Fetching transcript and generating tags..."):
            transcript = get_youtube_transcript_text(video_id)
            if transcript:
                tags = generate_tags_with_gemini(transcript, api_key) # Pass api_key
            else:
                tags = None

        st.subheader("Transcript:")
        st.text_area("Malayalam Transcript", transcript, height=300)

        if tags:
            st.subheader("Generated Tags:")
            # Create the HTML for the tag cloud
            tag_cloud_html = '<div class="tag-cloud">'
            for tag in tags:
                tag_cloud_html += f'<span class="tag">{tag}</span>'
            tag_cloud_html += '</div>'

            st.markdown(tag_cloud_html, unsafe_allow_html=True)  # Render as HTML
    else:
        st.error("Invalid YouTube URL. Please enter a valid URL.")
import os
import json
import requests
from bs4 import BeautifulSoup
from google import genai
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def fetch_hiphop_releases_page():
    print("Fetching Hip-Hop releases from Wikipedia...")
    url = "https://en.wikipedia.org/wiki/2026_in_hip_hop"
    
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text()[:15000]
    except Exception as e:
        print(f"Error fetching Wikipedia page: {e}")
        return ""
    
def extract_albums_with_gemini(raw_text):
    print("Gemini is analyzing the text to extract Hip-Hop albums...")
    client = genai.Client(api_key=GEMINI_KEY)
    
    prompt = f"""
    You are a hip hop music analyst. I need you to analyze the following text and extract a list of hip hop albums 
    released or set to be released in 2026. Return ONLY a valid and clean JSON array of objects. Do not wrap it in json or markdown blocks.
    Each object should have the following keys: "artist", "album", "release_date", "spotify_link" (if available),
    "status" (either "released" or "upcoming").
    Text to analyze:
    {raw_text}
    """
    
    response = client.models.generate_content(
        model = "gemini-2.5-flash",
        contents = prompt
    )
    return response.text.strip()

def get_spotify_token():
    auth_url = "https://accounts.spotify.com/api/token"
    res = requests.post(auth_url, {
        "grant_type": "client_credentials",
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    })
    return res.json().get("access_token")

def check_album_on_spotify(token, artist, album):
    search_url = f"https://api.spotify.com/v1/search?q=artist:{artist}%20album:{album}&type=album&limit=1"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(search_url, headers=headers).json()
        items = res.get("albums", {}).get("items", [])
        if items:
            spotify_url = items[0].get("external_urls", {}).get("spotify", "")
            return f"Album LIVE, listen here: {spotify_url}"
        return "Album not live on Spotify yet."
    except Exception as e:
        print(f"Error checking Spotify: {e}")
        return ""
    
def main():
    if not all ([GEMINI_KEY, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, DISCORD_WEBHOOK_URL]):
        print("Please set all required environment variables.")
        return ""
    
    raw_data = fetch_hiphop_releases_page()
    
    try: 
        ai_output = extract_albums_with_gemini(raw_data)

        albums_list = json.loads(ai_output)
    except Exception as e:
        print(f"Error parsing Gemini JSON output: {e}")
        return ""
    
    print ("Number of analyzed albums: ", len(albums_list))
    spotify_token = get_spotify_token()
    
    discord_message = "**Hip-Hop Album Releases in 2026**\n\n"
    discord_message += " --- "
    
    for item in albums_list[:10]:
        artist = item.get("artist")
        album = item.get("album")
        
        status = check_album_on_spotify(spotify_token, artist, album)
        discord_message += f"**{artist} - {album}**\nStatus: {status}\n\n"
    
    response = requests.post(DISCORD_WEBHOOK_URL, json={"content": discord_message})
    
    if response.status_code != 204:
        print(f"Failed to send Discord message: {response.text}")
    else:
        print("Discord message sent successfully.")
    
if __name__ == "__main__":
    main()
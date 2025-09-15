# main.py

import tkinter as tk
import threading
import time
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from slack_sdk import WebClient
import requests
from requests.auth import HTTPBasicAuth
from flask import Flask, redirect, request
import base64
import os

running = False
flask_process = None
recent_stop = False

class SpotifySlackStatus:
    def __init__(self, shutting_down=False):
        self.parse_config()
        self.slack_client = WebClient(token=self.slack_client_token)
        if not shutting_down:
            self.get_spotify_acccess_token()

    def parse_config(self) -> None:
        """
        get the necesasry creds from the config file
        """
        with open("./src/conf", "r") as infile:
            lines = infile.readlines()
        if len(lines) == 0:
            raise Exception("Invalid config file")
        for line in lines:
            if line.startswith("slack_client_token"):
                self.slack_client_token = line.split("=")[1].strip()
            elif line.startswith("spotify_username"):
                self.spotify_username = line.split("=")[1].strip()
            elif line.startswith("spotify_password"):
                self.spotify_password = line.split("=")[1].strip()

    def read_oauth_code(self):
        """
        get the oauth token from the file where it's stored
        this is because there's no browser session to store it
        """
        with open("./src/oauth_code", "r") as infile:
            lines = infile.readlines()
        return lines[0].strip() if len(lines) > 0 else None

    def update_slack_status(self, status_text, status_emoji):
        """
        update slack with the text and emoji for the user status
        """
        try:
            response = self.slack_client.users_profile_set(
                profile={
                    "status_text": status_text,
                    "status_emoji": status_emoji
                }
            )
            return response
        except Exception as e:
            print(f"Error updating Slack status: {e}")
            return None
        
    def get_spotify_acccess_token(self, refresh=False):
        """
        use the oauth flow to get a token from spotify to use for getting current playing song
        """
        url = "https://accounts.spotify.com/api/token"
        creds = f"{self.spotify_username}:{self.spotify_password}"
        encoded_creds = base64.b64encode(creds.encode()).decode("utf-8")
        headers = {'content-type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {encoded_creds}'}
        
        if not refresh:
            if os.path.exists("./src/access_token"):
                with open("./src/access_token", "r") as infile:
                    lines = infile.readlines()
                    self.spotify_access_token = lines[0].strip()
                    return
            oauth_code = self.read_oauth_code()
            if oauth_code is None:
                print("oauth_code is None")
                return
            data = {"code": oauth_code, "redirect_uri": "http://127.0.0.1:3000/callback", "grant_type": "authorization_code"}
            response = requests.post(url, headers=headers, data=data)
            if response.status_code == 200:
                print(f"token response: {response.json()}")
                access_token = response.json().get("access_token")
                refresh_token = response.json().get("refresh_token")
                self.spotify_access_token = access_token
                with open("./src/access_token", "w") as outfile:
                    outfile.write(access_token)
                with open("./src/refresh_token", "w") as outfile:
                    outfile.write(refresh_token)
            else:
                print(f"Error getting access token: {response.status_code}")  
        else:
            # if we're refreshing the token, we don't need to write a new refresh token from the response (there won't be one)
            print("refreshing access token")
            refresh_token = ""
            with open("./src/refresh_token", "r") as infile:
                lines = infile.readlines()
                refresh_token = lines[0].strip()
            data = {"grant_type": "refresh_token", "redirect_uri": "http://127.0.0.1:3000/callback", "refresh_token": refresh_token}
            response = requests.post(url, headers=headers, data=data)
            if response.status_code == 200:
                print(f"token response: {response.json()}")
                access_token = response.json().get("access_token")
                self.spotify_access_token = access_token
                with open("./src/access_token", "w") as outfile:
                    outfile.write(access_token)
            else:
                print(f"Error getting access token: {response.status_code}")  
        

    def get_current_playing_track(self):
        """
        query the slack api to get information about the currently playing track (if any)
        """
        try:
            response = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers={"Authorization": f"Bearer {self.spotify_access_token}"})
            if response.status_code == 200:
                data = response.json()
                if data and "item" in data:
                    track_name = data["item"]["name"]
                    artist_name = ", ".join(artist["name"] for artist in data["item"]["artists"])
                    album_year = data["item"]["album"]["release_date"][:4]
                    playing_info = f"{track_name} by {artist_name} - {album_year}"
                    if data["is_playing"]:
                        print(f"updating slack status to {playing_info}")
                        self.update_slack_status(playing_info, ":headphones:")
                    else:
                        print("clearing slack status")
                        self.update_slack_status("", "")
            elif response.status_code == 401:
                print("Spotify access token expired, refreshing...")
                self.get_spotify_acccess_token(refresh=True)
            elif response.status_code == 204:
                print("No track currently playing")
                self.update_slack_status("", "")    
            else:
                print(response.status_code)
                print(response.reason)
        except Exception as e:
            print(f"Error getting current playing track: {e}")

def start_flask_server():
    """
    run flask in a background process
    """
    global flask_process
    if flask_process is None:
        flask_process = subprocess.Popen(["python", "src/flask_server.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(2)
        print("Flask server started")
        threading.Thread(target=read_flask_output, daemon=True).start()

def read_flask_output():
    global flask_process
    if flask_process:
        for line in flask_process.stdout:
            print(f"[FLASK STDOUT] {line.strip()}")
        for line in flask_process.stderr:
            print(f"[FLASK STDERR] {line.strip()}")

def stop_flask_server():
    global flask_process
    if flask_process is not None:
        flask_process.terminate()
        flask_process.wait()
        flask_process = None

def run_slack_updater():
    """
    instantiate the SpotifySlackStatus class and update the slack status every 15 seconds (keeps spotify usage under the
    free threshold for a single user)
    """
    sss = SpotifySlackStatus()
    while running:
        time.sleep(15)
        sss.get_current_playing_track()

def start_action():
    """
    handle the tkinter action to start the process, start the flask server to handle oauth token requests, and
    lastely start the updater in a thread
    """
    print("Start button clicked")
    global running
    if running:
        print("Already running")
        return
    
    start_flask_server()
    if not os.path.exists("./src/access_token"):
        chrome_options = Options()
        chrome_options.add_argument(r"--user-data-dir=C:\Users\justi\AppData\Local\Google\Chrome\User Data")
        chrome_options.add_argument(r"--profile-directory=Default")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("http://127.0.0.1:3000/login")
        # Wait for the user to log in and authorize the app
        while "update" not in driver.current_url:
            time.sleep(1)
        driver.close()


    if not running:
        running = True
        threading.Thread(target=run_slack_updater, daemon=True).start()

def stop_action():
    """
    shut things down
    """
    print("Stop button clicked")
    global running
    if not running:
        print("Already stopped")
        return
    global recent_stop
    recent_stop = True
    stop_flask_server()

    if running:
        running = False
        time.sleep(15)
        # clear the Slack status when stopping
        sss = SpotifySlackStatus(shutting_down=True)
        sss.update_slack_status("", "")

def on_close():
    # shut things down
    stop_flask_server()
    global running
    running = False
    sss = SpotifySlackStatus(shutting_down=True)
    sss.update_slack_status("", "")
    app.destroy()

def position_window():
    """
    basic tkinter setup, this will make the tkinter window very small and tuck it into the
    bottom right corner of the screen
    """
    # Get screen width and height
    screen_width = app.winfo_screenwidth()
    screen_height = app.winfo_screenheight()

    # Define window dimensions
    window_width = 150  # Adjust as needed
    window_height = 100  # Adjust as needed

    # Calculate position for bottom-right corner
    x = screen_width - window_width - 20  # 10px padding from the right edge
    y = screen_height - window_height - 75  # 50px padding from the bottom edge (accounts for taskbar)

    # Set the window geometry
    app.geometry(f"{window_width}x{window_height}+{x}+{y}")

app = tk.Tk()
app.title("Tkinter Application")

position_window()

app.protocol("WM_DELETE_WINDOW", on_close)  # Bind the on_close function to window close event

start_button = tk.Button(app, text="Start", command=start_action)
start_button.pack(pady=10)

stop_button = tk.Button(app, text="Stop", command=stop_action)
stop_button.pack(pady=10)

app.mainloop()
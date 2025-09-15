from flask import Flask, redirect, request

app = Flask(__name__)


def get_spotify_client_id():
    # Read the Spotify app credentials from a file
    spotify_cilent_id = ""
    with open("./src/conf", "r") as file:
        lines = file.readlines()
        for line in lines:
            if line.startswith("spotify_username"):
                spotify_client_id = line.split("=")[1].strip()
    return spotify_client_id

@app.route('/login')
def login():
    """
    login and use the /callback route as the target for the callback
    """
    client_id = get_spotify_client_id()
    scope = "user-read-currently-playing"
    return redirect(f"https://accounts.spotify.com/authorize?response_type=code&client_id={client_id}&redirect_uri=http://127.0.0.1:3000/callback&scope={scope}")

@app.route('/callback')
def callback():
    """
    save the oauth token to a file because we don't have a browser session to store it
    """
    oauth_code = request.args.get('code')
    with open("./src/oauth_code", "w") as outfile:
        outfile.write(oauth_code)
    return redirect("/update")

@app.route('/update')
def update():
    return "success"

if __name__ == '__main__':
    app.run(port=3000)
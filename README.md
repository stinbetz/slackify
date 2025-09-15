# Tkinter Application

This project is a simple Tkinter application that demonstrates the creation of a GUI with two buttons: "Start" and "Stop".

## Project Structure

```
tkinter-app
├── src
│   ├── main.py
|   ├── flask_server.py
├── requirements.txt
└── README.md
```

## Requirements

To run this application, you need to have Python installed on your machine. The required dependencies are listed in the `requirements.txt` file.

## Installation

1. Clone the repository or download the project files.
2. Navigate to the project directory.
3. Install the required dependencies using the following command:

```
pip install -r requirements.txt
```

## Running the Application

Before running this application, you will need a compatible version of chromedriver, place it in the /src/ directory.  You will also need a conf file in the /src/ directory with 3 items:  
1. slack_client_token=<your slack bot client token>  
2. spotify_username=<your user token for the spotify dev integration>  
3. spotify_password=<your user key for the spotify dev integration>  
Note: setting up your slack bot and spotify dev integration are beyond the scope of this project, but are both well documented by their respective companies.  

To run the application, execute the following command:

```
python src/main.py
```

This will open a window with "Start" and "Stop" buttons. You can click these buttons to see their functionality.

## License

This project is open-source and available under the MIT License.
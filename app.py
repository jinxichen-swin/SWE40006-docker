import os
import socket
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "Docker Web App")
APP_COLOR = os.getenv("APP_COLOR", "#4a90d9")

@app.route("/")
def home():
    return f"""
    <html><body style="font-family:sans-serif;background:{APP_COLOR};color:white;text-align:center;padding-top:80px">
      <h1>{APP_NAME}</h1>
      <p>Container host: {socket.gethostname()}</p>
      <p>Served at: {datetime.now():%Y-%m-%d %H:%M:%S}</p>
    </body></html>
    """

@app.route("/health")
def health():
    return jsonify(status="ok")
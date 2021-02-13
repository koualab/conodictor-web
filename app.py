import os
from flask import Flask, render_template

app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/run", methods=["GET", "POST"])
def run():
    return render_template("run.html")


if __name__ == "__main__":
    app.run(debug=True)

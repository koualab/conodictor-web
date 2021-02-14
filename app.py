import os
from flask import Flask, render_template

# from werkzeug.utils import secure_filename

# from flask_sqlalchemy import SQLAlchemy

from forms import RunForm

# from models import Result

app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# db = SQLAlchemy(app)
UPLOAD_PATH = "/tmp"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/run", methods=["GET", "POST"])
def run():
    form = RunForm()

    return render_template("run.html", form=form)


"""
@app.route("/results", methods=["POST"])
def results():


    if Request.form.get("fileForm"):
        inpath = secure_filename(Request.form["fileForm"])
    elif Request.form.get("textareaForm"):
        open(os.path.join(UPLOAD_PATH, Request.form["jobForm"]), "w").write(
            Request.form.get("textareaForm")
        )

"""


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True)

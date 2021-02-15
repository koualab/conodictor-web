import os
from flask import Flask
from flask import flash, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename

from forms import RunForm


UPLOAD_FOLDER = "./tmp"
ALLOWED_EXTENSIONS = {"fa", "fas", "fasta", "fna", "gz"}

app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    """Function to test for allowed files."""

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/run", methods=["GET", "POST"])
def run():
    form = RunForm()
    if request.method == "POST":
        # get file uploaded by the user
        text = request.form["uploaded_text"]
        infile = request.files["uploaded_file"]
        email = request.form["email"]

        if infile.filename == "" and not text:
            flash("No selected file nor input data.")
            return redirect(request.url)

        if infile and allowed_file(infile.filename):
            # Upload file
            filename = secure_filename(infile.filename)
            infile.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            return redirect(url_for("results"))

        if infile and not allowed_file(infile.filename):
            # Provided file is not supported
            flash(
                f"Your provided file {infile.filename}"
                + " is not supported. Please provide a fasta file"
                + " either gzipped or not."
            )
            return redirect(request.url)

        if text and not infile:
            open(
                os.path.join(app.config["UPLOAD_FOLDER"], form.job_id.data),
                "w",
            ).write(form.uploaded_text.data)
            return redirect(url_for("results"))

        if email:
            flash("Got email")

    return render_template("run.html", form=form)


@app.route("/results")
def results():
    return render_template("results.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True)

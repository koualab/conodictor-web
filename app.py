import os
import subprocess
from flask import Flask, abort
from flask import flash, request, render_template, redirect, url_for, session
from sqlalchemy.orm.session import Session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from forms import RunForm
import models

UPLOAD_FOLDER = "./tmp"
RESULT_FOLDER = "./res"
ALLOWED_EXTENSIONS = {"fa", "fas", "fasta", "fna", "gz"}
app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULT_FOLDER"] = RESULT_FOLDER
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


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
        if form.validate_on_submit():
            # get file uploaded by the user
            text = request.form["uploaded_text"]
            infile = request.files["uploaded_file"]
            email = request.form["email"]
            jobname = request.form["job_id"]

            if infile.filename == "" and not text:
                flash("No selected file nor input data.")
                return redirect(request.url)

            if infile and allowed_file(infile.filename):
                # Upload file
                filename = secure_filename(infile.filename)
                path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                infile.save(path)
                session["path"] = path
                session["jobname"] = jobname
                session["resout"] = os.path.join(
                    app.config["RESULT_FOLDER"], jobname
                )
                return redirect(url_for("results", jobname=jobname))

            if infile and not allowed_file(infile.filename):
                # Provided file is not supported
                flash(
                    f"Your provided file {infile.filename}"
                    + " is not supported. Please provide a fasta file"
                    + " either gzipped or not."
                )
                return redirect(request.url)

            if text and not infile:
                path = os.path.join(
                    app.config["UPLOAD_FOLDER"], form.job_id.data
                )
                open(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"], form.job_id.data
                    ),
                    "w",
                ).write(form.uploaded_text.data)
                session["path"] = path
                session["jobname"] = jobname
                session["resout"] = os.path.join(
                    app.config["RESULT_FOLDER"], jobname
                )
                return redirect(url_for("results", jobname=jobname))

            if email:
                flash("Got email")

            results = [
                jobname,
                email,
                os.path.join(app.config["RESULT_FOLDER"], jobname),
            ]
            result = models.Result(
                job_name=results[0], email=results[1], result_url=results[2]
            )
            db.session.add(result)
            db.session.commit()

    return render_template(
        "run.html",
        form=form,
    )


@app.route("/results/<jobname>", methods=["GET", "POST"])
def results(jobname):

    # Jobname in db. We test provided jobname against the stored jobname
    # For returning peoples who want to have access to their old results
    # our_jobname = Session.query(models.Result).filter_by(jobname=jobname)

    # Here we put the session variable in the list and also the stored jobname
    VALID_JOBNAME = [session["jobname"]]
    # VALID_JOBNAME.extend(our_jobname.jobname)

    if jobname not in VALID_JOBNAME:
        abort(400)

    inpath = session["path"]
    jobname = session["jobname"]
    resout = session["resout"]

    # subprocess.run(["/home/sinfo/projects/conodictor",
    # f"-o{resout}", inpath])

    return render_template(
        "results.html", inpath=inpath, resout=resout, jobname=jobname
    )


@app.route("/results", methods=["GET", "POST"])
def res_():
    flash("Please enter data before trying to get the results")
    return redirect(url_for("run"))


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True)

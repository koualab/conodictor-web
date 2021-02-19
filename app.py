from conodictor import conodictor
from flask import Flask, abort
from flask import flash, request, render_template, redirect, url_for, session
from flask.helpers import send_from_directory
from forms import RunForm
import os
from rq import Queue
from rq.job import Job
from werkzeug.utils import secure_filename
from worker import conn


UPLOAD_FOLDER = "tmp"
RESULT_FOLDER = "res"


app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULT_FOLDER"] = RESULT_FOLDER

q = Queue(connection=conn)

ALLOWED_EXTENSIONS = {"fa", "fas", "fasta", "fna", "gz"}
DNA = "ATCG"
PROTEINS = "ABCDEFGHIKLMNPQRSTVWXYZ"


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def allowed_text(text):
    return all(i in DNA for i in text.upper()) or all(
        i in PROTEINS for i in text.upper()
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/run", methods=["GET", "POST"])
def run():
    form = RunForm()

    if request.method == "POST" and form.validate():
        file = request.files["uploaded_file"]
        text = request.form["uploaded_text"]
        jobname = request.form["job_id"]

        # If a file is not selected for upload...
        if file.filename == "":
            # ...and a sequence is not also provided
            if text == "":
                flash("No data submitted. Please check your input.")
                return redirect(request.url)
            # ...and a sequence is provided but is not DNA or proteins
            elif text != "" and not allowed_text(text):
                flash("Input data is not DNA nor proteins.")
                return redirect(request.url)
            # ...and a sequence is provided and is DNA or proteins
            elif text != "" and allowed_text(text):
                path = os.path.join(
                    app.config["UPLOAD_FOLDER"], form.job_id.data
                )
                open(
                    path,
                    "w",
                ).write(form.uploaded_text.data)
                session["path"] = path
                session["jobname"] = jobname
                session["resout"] = os.path.join(
                    app.config["RESULT_FOLDER"], jobname
                )
                return render_template(
                    "run.html",
                    form=form,
                    path=path,
                    jobname=jobname,
                    resout=session["resout"],
                )
        # If a file is selected for upload...
        elif file.filename != "":
            # ...and the filename is allowed
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(path)

                session["path"] = path
                session["jobname"] = jobname
                session["resout"] = os.path.join(
                    app.config["RESULT_FOLDER"], jobname
                )
                return render_template(
                    "run.html",
                    form=form,
                    path=path,
                    jobname=jobname,
                    resout=session["resout"],
                )
            # ...and the filename is not allowed
            else:
                flash(
                    "Provided file is not supported. Please select"
                    + " a fasta file either gzipped or not."
                )
                return redirect(request.url)

    return render_template("run.html", form=form)


@app.route("/results/jobkey", methods=["GET", "POST"])
def results(jobkey):
    jobname = jobkey
    if jobname in session:
        job = Job.fetch(jobname, connection=conn)
        if job.is_finished:
            return redirect(url_for("results", jobid=jobname))
        else:
            flash("Your job is not yet finished. Please come back later.")
            return redirect(url_for("results"))
    elif jobname not in session:
        if request.method == "POST":
            inpath = session["path"]
            jobname = session["jobname"]
            resout = session["resout"]

            job = q.enqueue_call(
                func=conodictor,
                args=(
                    inpath,
                    resout,
                ),
                result_ttl=5000,
            )
            dpath = os.path.join(app.config["RESULT_FOLDER"], job.get_id())
        elif request.method == "GET":
            flash(
                "Your jobid was not found."
                + " Please run a job before seeing any result"
            )
            return redirect(url_for("results"))
        else:
            abort(404)

    return render_template(
        "results.html",
        inpath=inpath,
        jobname=jobname,
        jobid=job.get_id(),
        dpath=dpath,
    )


@app.route("//<jobkey>", methods=["GET"])
def download(jobkey):

    job = Job.fetch(jobkey, connection=conn)

    if job.is_finished:
        return send_from_directory(app.config["RESULT_FOLDER"], jobkey)
    else:
        path = os.path.join(app.config["RESULT_FOLDER"], jobkey)
        return redirect(url_for("results", path))


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True)

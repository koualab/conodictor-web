"""Form object declaration."""
from wtforms import Form, StringField, FileField, TextAreaField
from wtforms.validators import DataRequired
import string
import random
import datetime


def jobid_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """Create random Job name."""
    rd = "".join(random.choice(chars) for _ in range(size))
    dt = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    return f"CONODICTOR_{rd}_{dt}"


class RunForm(Form):
    """Run ConoDictor form."""

    uploaded_file = FileField(
        "Select input DNA or proteins fasta file"
        + " (gzipped compressed files are accepted)"
    )
    uploaded_text = TextAreaField("or paste your sequence here")
    job_id = StringField(
        "Your Job name",
        [DataRequired()],
        default=jobid_generator(),
    )

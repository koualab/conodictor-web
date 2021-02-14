"""Form object declaration."""
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, TextAreaField
from wtforms.validators import Email, DataRequired

import string
import random
import datetime


def jobid_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """Create random Job name."""
    rd = "".join(random.choice(chars) for _ in range(size))
    dt = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    return f"CONODICTOR_{rd}_{dt}"


class RunForm(FlaskForm):
    """Run ConoDictor form."""

    uploaded_file = FileField("Select input fasta file")
    uploaded_text = TextAreaField("or paste your sequence here")
    email = StringField(
        "Get notified by email when the results are available",
        [Email(message=("Your input email is not correct"))],
    )
    job_id = StringField(
        "Your Job name",
        [DataRequired()],
        default=jobid_generator(),
    )

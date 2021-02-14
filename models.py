from app import db


class Result(db.Model):
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String())
    result_url = db.Column(db.String())

    def __init__(self, id, job_name, result_url):
        self.job_name = job_name
        self.result_url = result_url

    def __repr__(self):
        return "<id f{self.id}>"

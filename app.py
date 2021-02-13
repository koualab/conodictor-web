import os
from flask import Flask
from rq import Queue
from rq.job import Job
from worker import conn

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

q = Queue(connection=conn)

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')



@app.route('/run', methods=['GET', 'POST'])
def run():
    return render_template('run.html')



if __name__ == '__main__':
    app.run()
    
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
    errors = []
    results = {}
    if request.method == "POST":
        try:
            url = request.form['url']
            r = requests.get(url)
            print(r.text)
        except:
            errors.append(
                "Unable to get URL. Please make sure it's valid and try again."
            )
        
    return render_template('index.html', errors=errors, results=results)



if __name__ == '__main__':
    app.run()
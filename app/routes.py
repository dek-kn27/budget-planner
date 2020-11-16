from app import app

@app.route('/api/v1/hello-world-<id>')
def index(id):
    return 'Hello World {}'.format(id)

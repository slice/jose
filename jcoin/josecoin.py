from sanic import Sanic

app = Sanic()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8696)

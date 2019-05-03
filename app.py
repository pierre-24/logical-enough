import commons
import views_api

app, api = commons.create_app()


# APP
@app.route('/')
def hello_world():
    return 'Hello World!'


# API
api.add_resource(views_api.CheckMatch, '/api/check')


if __name__ == '__main__':
    app.run()

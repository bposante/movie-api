from google.cloud import datastore
from flask import Flask, request, render_template
import uuid
import movies
import movie_collections
import jwt
from util import *

app = Flask(__name__)
app.register_blueprint(movies.bp)
app.register_blueprint(movie_collections.bp)
client = datastore.Client()
users = "users"


@app.route('/', methods=['GET', 'POST'])
def welcome():
    if request.method == 'GET':
        return render_template('home.html')

    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # check to see if user exists
        query = client.query(kind=users)
        query.add_filter("username", "=", username)
        results = list(query.fetch())
        new_user = False
        if len(results) < 1:
            # add user
            new_user = True
            user_id = str(uuid.uuid4())
            user = datastore.Entity(key=client.key(users))
            user.update({
                'id': user_id,
                'username': username,
                'password': password
            })
            client.put(user)

        # make sure password is correct - need another page to render if not
        else:
            current_user = results[0]
            user_id = current_user['id']
            if current_user['password'] != password:
                return render_template('incorrect_password.html')

        encoded = jwt.encode({"user_id": user_id}, jwt_key, algorithm="HS256")
        return render_template('userinfo.html', username=username, jwt=encoded, id=user_id, is_new=new_user)


@app.route('/users', methods=['GET'])
def users_get():
    res = accept_type_validation(['application/json'])
    if res != None:
        return res
    all_users = get_entity(users, False, '')
    return all_users


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

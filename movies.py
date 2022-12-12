from google.cloud import datastore
from flask import Blueprint, request
from util import *
import json


client = datastore.Client()
bp = Blueprint('movies', __name__, url_prefix='/movies')
movies = 'movies'


@bp.route('', methods=['POST', 'GET'])
def movies_get_post():
    if request.method == 'GET':
        all_movies = get_entity(movies, True, "")
        return all_movies

    elif request.method == 'POST':
        content, res = request_validation()
        if res != None:
            return res
        res = accept_type_validation(['application/json'])
        if res != None:
            return res

        content = request.get_json()

        if ("name" in content) and ("genre" in content) and ("length" in content):
            if content["length"] < 0:
                return create_response("", 400, error=errors["length"])

            if unique_name(content['name'], movies):
                new_movie = datastore.Entity(key=client.key(movies))
                new_movie.update(
                    {
                        "name": content["name"],
                        "genre": content["genre"],
                        "length": content["length"],
                        "collections": []
                    }
                )
                client.put(new_movie)

                movie_key = client.key(movies, new_movie.key.id)
                movie = client.get(key=movie_key)
                movie.update(
                    {
                        "self": f"{request.url}/{new_movie.key.id}"
                    }
                )
                client.put(movie)
                movie["id"] = new_movie.key.id
                return create_response(json.dumps(movie), 201)

            else:
                return create_response("", 403, error=errors["name"])

        else:
            return create_response("", 400, error=errors["missing"])


@bp.route('/<id>', methods=['GET', 'PATCH', 'PUT', 'DELETE'])
def movie_get_patch_delete(id):
    if request.method == 'GET':
        movie_key = client.key(movies, int(id))
        movie = client.get(key=movie_key)
        if movie:
            movie["id"] = int(id)
            return create_response(json.dumps(movie), 200)
        else:
            return create_response("", 404, error=errors["invalidId"])

    elif request.method == 'PUT':
        content, res = request_validation()
        if res != None:
            return res
        res = accept_type_validation(['application/json'])
        if res != None:
            return res
        content = request.get_json()

        if ("name" in content) and ("genre" in content) and ("length" in content):

            movie_key = client.key(movies, int(id))
            movie = client.get(key=movie_key)

            if unique_name(content['name'], movies):

                if content["length"] < 0:
                    return create_response("", 400, error=errors["length"])

                if movie:
                    movie.update(
                        {
                            "name": content["name"],
                            "genre": content["genre"],
                            "length": content["length"],
                            "collections": movie["collections"]
                        }
                    )
                    client.put(movie)
                    movie["id"] = int(id)
                    return create_response(json.dumps(movie), 303, location=movie['self'])

                else:
                    return create_response("", 404, error=errors["invalidId"])

            else:
                return create_response("", 403, error=errors["name"])

        else:
            return create_response("", 400, error=errors["missing"])

    elif request.method == 'PATCH':
        content, res = request_validation()
        if res != None:
            return res
        res = accept_type_validation(['application/json'])
        if res != None:
            return res

        content = request.get_json()
        movie_key = client.key(movies, int(id))
        movie = client.get(key=movie_key)
        if movie:
            movie_name = content['name'] if "name" in content else movie['name']
            movie_genre = content['genre'] if "genre" in content else movie['genre']
            movie_length = content['length'] if "length" in content else movie['length']

            if movie_length < 0:
                return create_response('', 400, errors['length'])

            if (movie_name != movie['name'] and unique_name(movie_name, movies)) or (movie_name == movie['name']):
                movie.update(
                    {
                        "name": movie_name,
                        "genre": movie_genre,
                        "length": movie_length,
                        "collections": movie["collections"]
                    }
                )
                client.put(movie)
                movie['id'] = int(id)
                return create_response(json.dumps(movie), 200)

            else:
                return create_response('', 403, errors['name'])

        else:
            return create_response('', 404, errors['invalidId'])

    elif request.method == 'DELETE':
        movie_key = client.key(movies, int(id))
        movie = client.get(key=movie_key)

        if movie:

            query = client.query(kind="collections")
            results = list(query.fetch())
            for collection in results:
                if movie.key.id in collection["movies"]:
                    collection["movies"].remove(movie.key.id)
                    collection.update({"movies": collection["movies"]})
                    client.put(collection)

            client.delete(movie_key)
            return create_response("", 204)

        else:
            return create_response('', 404, errors['invalidId'])

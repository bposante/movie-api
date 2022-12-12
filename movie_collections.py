from google.cloud import datastore
from flask import Blueprint, request
from util import *
import json


client = datastore.Client()
bp = Blueprint('collections', __name__, url_prefix='/collections')
collections = "collections"
movies = "movies"


@bp.route('', methods=['POST', 'GET'])
def collections_post_get():
    if request.method == 'POST':
        content, res = request_validation()
        if res != None:
            return res
        res = accept_type_validation(['application/json'])
        if res != None:
            return res

        content = request.get_json()
        encrypted_jwt = request.headers.get("Authorization")

        if not encrypted_jwt:
            return create_response(json.dumps({"Error": "Invalid token"}), 401)

        user_id = get_id_from_jwt(encrypted_jwt)

        if content.get("name") == None or content.get("genre") == None or content.get("description") == None:
            return create_response('', 400, error=errors['missing'])

        if not unique_name(content.get("name"), collections, user_id):
            return create_response('', 400, error=errors['name'])

        new_collection = datastore.entity.Entity(key=client.key(collections))
        new_collection.update({"name": content["name"],
                               "genre": content["genre"],
                               "description": content["description"],
                               "movies": [],
                               "user_id": user_id,
                               "self": request.root_url + "collections/" + str(new_collection.key.id)})

        client.put(new_collection)

        res_body = json.dumps({
            "id": new_collection.key.id,
            "name": new_collection["name"],
            "genre": new_collection["genre"],
            "description": new_collection["description"],
            "movies": new_collection["movies"],
            "user_id": user_id,
            "self": request.root_url + "collections/" + str(new_collection.key.id)})
        return create_response(res_body, 201)

    elif request.method == 'GET':
        res = accept_type_validation(['application/json'])
        if res != None:
            return res
        encrypted_jwt = request.headers.get("Authorization")

        if not encrypted_jwt:
            return create_response('', 401, error=errors['invalidToken'])

        user_id = get_id_from_jwt(encrypted_jwt)

        if not user_id:
            return create_response('', 401, error=errors['invalidToken'])

        all_collections = get_entity(collections, True, user_id)
        return all_collections


@bp.route('/<collection_id>', methods=['GET', 'DELETE', 'PUT', 'PATCH', 'POST'])
def collections_get_delete_update(collection_id):
    if not collection_id:
        return create_response('', 404, error=errors['invalidId'])

    collections_key = client.key(collections, int(collection_id))
    collection = client.get(key=collections_key)
    encrypted_jwt = request.headers.get("Authorization")

    if not encrypted_jwt:
        # not authorized
        return create_response(json.dumps({"Error": "Invalid token"}), 401)

    user_id = get_id_from_jwt(encrypted_jwt)

    if collection and user_id != collection['user_id']:
        # not the owner of the collection
        return create_response('', 403)

    if request.method == 'GET':
        if collection:
            res_body = json.dumps({
                "id": collection.key.id,
                "name": collection["name"],
                "description": collection["description"],
                "genre": collection["genre"],
                "movies": collection["movies"],
                "user_id": collection["user_id"],
                "self": request.root_url + "collections/" + str(collection.key.id)})
            return create_response(res_body, 200)

        else:
            return create_response('', 404, error=errors['invalidId'])

    elif request.method == 'PATCH':
        content, res = request_validation()
        if res != None:
            return res
        res = accept_type_validation(['application/json'])
        if res != None:
            return res

        if collection:
            if content.get("name") == None and content.get("description") == None and content.get("genre") == None:
                return create_response('', 400, error=errors['missingAll'])

            if content.get("name") != None:
                if unique_name(content.get("name"), movies, user_id):
                    collection.update({"name": content["name"]})
                else:
                    return create_response('', 403, error=errors['name'])

            if content.get("description") != None:
                collection.update({"description": content["description"]})

            if content.get("genre") != None:
                collection.update({"genre": content["genre"]})

            client.put(collection)
            res_body = json.dumps({
                "id": collection.key.id,
                "name": collection["name"],
                "description": collection["description"],
                "genre": collection["genre"],
                "movies": collection["movies"],
                "user_id": collection["user_id"],
                "self": request.root_url + "collections/" + str(collection.key.id)})

            return create_response(res_body, 200)

        else:
            return create_response("", 404, error=errors['invalidId'])

    elif request.method == 'PUT':
        content, res = request_validation()
        if res != None:
            return res

        if collection:
            if content.get("name") == None or content.get("description") == None or content.get("genre") == None:
                return create_response('', 400, errors['missing'])

            collection.update({"name": content["name"]})
            collection.update({"description": content["description"]})
            collection.update({"genre": content["genre"]})

            client.put(collection)
            collection_self = request.root_url + \
                "collections/" + str(collection.key.id)
            return create_response('', 303, location=collection_self)

        else:
            return create_response('', 404, errors['invalidId'])

    elif request.method == 'DELETE':

        if collection:
            query = client.query(kind=movies)
            results = list(query.fetch())
            for movie in results:
                if collection.key.id in movie["collections"]:
                    movie["collections"].remove(collection.key.id)
                    movie.update({"collections": movie["collections"]})
                    client.put(movie)
            client.delete(collections_key)
            return ('', 204)

        else:
            return create_response('', 404, errors['invalidId'])


@bp.route('/<collection_id>/movies/<movie_id>', methods=['PUT', 'DELETE'])
def collections_and_movies(collection_id, movie_id):

    if not collection_id or not movie_id:
        return create_response('', 404, error=errors['invalidId'])

    collection_key = client.key(collections, int(collection_id))
    collection = client.get(key=collection_key)

    encrypted_jwt = request.headers.get("Authorization")

    if not encrypted_jwt:
        return create_response(json.dumps({"Error": "Invalid token"}), 401)

    user_id = get_id_from_jwt(encrypted_jwt)
    if collection and (user_id != collection['user_id']):
        return create_response('', 403, error=errors['invalidToken'])

    movie_key = client.key(movies, int(movie_id))
    movie = client.get(key=movie_key)

    if request.method == 'PUT':
        res = accept_type_validation(['application/json'])
        if res != None:
            return res

        if collection and movie:
            movies_array = collection["movies"]
            collections_array = movie["collections"]
            movies_array.append(movie.key.id)
            collections_array.append(collection.key.id)

            collection.update({"movies": movies_array})
            movie.update({"collections": collections_array})
            client.put(collection)
            client.put(movie)

            return create_response('', 204)

        else:
            return create_response('', 404, errors['notExist'])

    elif request.method == 'DELETE':
        res = accept_type_validation(['application/json'])
        if res != None:
            return res

        if collection:
            movies_array = collection["movies"]
            collections_array = movie["collections"]

            if movie.key.id not in movies_array:
                return create_response('', 404, errors['notExist'])

            movies_array.remove(movie.key.id)
            collections_array.remove(collection.key.id)

            collection.update({"movies": movies_array})
            movie.update({"collections": collections_array})
            client.put(collection)
            client.put(movie)
            return create_response('', 204)

        elif not collection or not movie:
            return create_response('', 404, errors['notExist'])

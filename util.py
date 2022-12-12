# Various utility functions to make some things simpler

from google.cloud import datastore
from flask import request, Response
import json
import jwt

client = datastore.Client()
jwt_key = "secret"
errors = {
    "length": "The length must be greater than 0",
    "name": "The name must be unique",
    "missing": "The request object is missing at least one of the required attributes",
    "missingAll": "The request object is missing any recognized attributes",
    "invalidId": "No entity with this ID exists",
    "invalidToken": "Invalid token",
    "notExist": "The specified collection and/or movie does not exist"
}


def create_response(body, status, error=None, location=""):
    if error:
        body = json.dumps({"Error": error})
    res = Response(response=body, status=status, mimetype="application/json")
    res.headers.set('Content-Type', 'application/json; charset=utf-8')
    if location:
        res.headers.set('Location', location)
    return res


def accept_type_validation(accept_mimetypes):
    res = None
    matches = [
        value for value in accept_mimetypes if value in request.accept_mimetypes]
    if len(matches) < 1:
        res_body = json.dumps(
            {"Error": "No match was found between the request's Accept header and the available options for this endpoint"})
        res = Response(response=res_body, status=406,
                       mimetype="application/json")
        res.headers.set('Content-Type', 'application/json; charset=utf-8')
    return res


def get_entity(entity_type, pagination, user_id):
    query = client.query(kind=entity_type)
    if user_id:
        query.add_filter("user_id", "=", user_id)
    if pagination:
        q_limit = int(request.args.get('limit', '5'))
        q_offset = int(request.args.get('offset', '0'))
        l_iterator = query.fetch(limit=q_limit, offset=q_offset)
        pages = l_iterator.pages
        results = list(next(pages))

        if l_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + \
                str(q_limit) + "&offset=" + str(next_offset)
        else:
            next_url = None

        for result in results:
            result["id"] = result.key.id
            result["self"] = request.root_url + \
                entity_type + "/" + str(result.key.id)
        output = {entity_type: results}
        if next_url:
            output["next"] = next_url

        return create_response(json.dumps(output), 200)
    else:
        results = list(query.fetch())

    for result in results:
        result["id"] = result.key.id
        result["self"] = request.root_url + \
            entity_type + "/" + str(result.key.id)

    return create_response(json.dumps(results), 200)


def request_validation():
    res = None
    content = None
    try:
        content = request.get_json()
    except:
        res_body = json.dumps(
            {"Error": "Only application/json MIMEtype is accepted"})
        res = create_response(res_body, 415)

    return content, res


def get_id_from_jwt(token):
    try:
        token = str.replace(token, 'Bearer ', '')
        payload = jwt.decode(token, jwt_key, algorithms="HS256")
        return payload['user_id']
    except:
        return None


def unique_name(name, entity_type, user_id=None):
    query = client.query(kind=entity_type)
    if user_id:
        query.add_filter("user_id", "=", user_id)
    results = list(query.fetch())
    for result in results:
        if result['name'] == name:
            return False
    return True

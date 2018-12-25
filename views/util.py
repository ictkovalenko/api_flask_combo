import inspect
from functools import wraps
from flask import g, url_for, session, redirect, request, make_response
from flaskapp import app
from components import obscure
from models.structure.user import User
from query.structure.projects_query import fetch_all_orgs_for_user


def text_view(func):
    @wraps(func)
    def with_text_view(*args, **kwargs):
        return "<pre>\n" + ("Logged in as %s\n" % g.user.email if g.user is not None else '') + "\n".join(func(*args, **kwargs)) + "\n</pre>"
    return with_text_view


def login_required(func):
    @wraps(func)
    def with_login_required(*args, **kwargs):
        if g.user is None:
            if 'authtoken' in session:
                user, status = User.get_from_token(session['authtoken'])
                g.user = user
        if g.user is None:
            return redirect('login')
        return func(*args, **kwargs)
    return with_login_required


def id_encode(num_id):
    return obscure.encode_tame(num_id)


def id_decode(enc_id):
    return obscure.decode_tame(enc_id)


def find_id(items, item_id):
    for i in items:
        if i.id == item_id:
            return i
    return None


class DataNotReadyException(Exception):
    pass


def download_view(func):
    @wraps(func)
    def with_download_view(*args, **kwargs):
        show = request.args.get('show', '0') == '1'
        test = request.args.get('test', '0') == '1'

        try:
            data, mime, filename = func(*args, **kwargs)
        except DataNotReadyException:
            return "Not Ready"

        if inspect.isgenerator(data):
            data = "\n".join(data)

        if test is True:
            resp = make_response("<pre>" + str(len(data)) + " bytes</pre>")
        elif show is False:
            resp = make_response(data)
            resp.headers["Content-Disposition"] = "attachment; filename=%s" % filename
            resp.mime_type = mime
        else:
            resp = make_response("<pre>" + data + "</pre>")

        return resp
    return with_download_view

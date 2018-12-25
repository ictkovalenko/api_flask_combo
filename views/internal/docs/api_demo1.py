import copy
from flask import json, render_template, url_for
from functools import wraps
from http import HTTPStatus
from flaskapp import app
from views.util import text_view

import requests


def TITLE(x):
    return "<h1>" + x + "</h1>"


def STEP(x):
    return "<h2>" + x + "</h2>"


def TXT(x):
    return x


def API_CALL(msg):
    err = ""
    err_cls = ""
    auth = ""
    if len(msg) > 4 and msg[4] != None:
        err = msg[4] + "\n"
        err_cls = "bg-danger"
    if len(msg) > 5 and msg[5] != None:
        auth = "Headers:\n  Auth-Token: " + msg[5][:20] + ("*"*len(msg[5][20:])) + "\n"

    req_txt = "<h4>" + msg[3] + " Request - " + msg[2] + "</h4><pre><code>" + auth + "Args:\n" + pjson(msg[0]) + "</code></pre>"
    rep_txt = "<h4>Reply</h4>" + "<pre class='" + err_cls + "'>" + err + "<code>" + pjson(msg[1]) + "</code></pre>"
    return req_txt + rep_txt


BASE = app.config['APIDOC_ADDR']


def pjson(d2):
    d = copy.deepcopy(d2)
    if 'password' in d:
        d['password'] = '******'
    if d and 'value' in d and d['value'] and 'auth_token' in d['value']:
        d['value']['auth_token'] = d['value']['auth_token'][:20] +("*"*len(d['value']['auth_token'][20:]))
    return json.dumps(d, sort_keys=True, indent=4, separators=(',', ': '))


def api_demo_view(func):
    @wraps(func)
    def with_text_view(*args, **kwargs):
        return render_template('docs/bootstrap.html', bodycontent="".join(func(*args, **kwargs)))
    return with_text_view


def api_post(ep, values, token):
    reply = requests.post(BASE + ep, json=values)
    js = json.loads(reply.content)
    return js, [values, js, ep, 'POST']


def api_get(ep, values, token):
    reply = requests.get(BASE + ep, params=values, headers={'Auth-Token': token})
    if reply.status_code != HTTPStatus.OK:
        err = "HTTPStatusCode: " + str(reply.status_code)
    else:
        err = None
    try:
        js = json.loads(reply.content)
    except:
        js = {}
    return js, [values, js, ep, 'GET', err, token]


def get_preconditions():
    value, msg = api_post('/api/1.0/authenticate', {
        'user_id': 'api@gmail.com',
        'password': 'xxx'},
                          None)

    token = value['value']['auth_token']

    return token, "XXX", "YYY"


@app.route('/internal/docs/api_examples')
@api_demo_view
def api_doc_toc_view():

    def out():
        yield TITLE("API Examples")

        yield TXT("<div><a href='" + url_for('api_doc_example2_view') + "'>Authorize and select a project</a></div>")
        yield TXT("<div><a href='" + url_for('api_doc_example3_view') + "'>Get activity data for a patient using therapeut login</a></div>")
        yield TXT("<div><a href='" + url_for('api_doc_example4_view') + "'>Get patient keys to allow patient access to data</a></div>")
        yield TXT("<div><a href='" + url_for('api_doc_example5_view') + "'>Get activity data for a patient using patient keys</a></div>")


    return out()


@app.route('/internal/docs/api_examples/2')
@api_demo_view
def api_doc_example2_view():

    def out():
        yield TITLE("Example: Authorize and select a project")

        yield STEP("Authorizing")
        yield TXT("First step is to acquire an auth token. This token must be passed in the header of API calls as 'Auth-Token'")
        value, msg = api_post('/api/1.0/authenticate', {
                              'user_id': 'api@gmail.com',
                              'password': 'XXX'},
                              None)
        yield API_CALL(msg)

        if 'value' in value and 'auth_token' in value['value']:
            token = value['value']['auth_token']
        else:
            return

        yield STEP("List Projects")
        yield TXT("A user can have access to multiple organizations and project. Find the correct one.")
        value, msg = api_get('/api/1.0/projects', {}, token)
        yield API_CALL(msg)

        if 'value' in value and 'organization' in value['value']:
            org_id = value['value'][0]['organization']['id']
            proj_id = value['value'][0]['projects'][2]['id']
        else:
            return

        yield TXT("In the following examples the ID of the organization (%s) and sens-demo project (%s) is user.<br><br>" % (org_id, proj_id))

    return out()


@app.route('/internal/docs/api_examples/3')
@api_demo_view
def api_doc_example3_view():

    token, org_id, proj_id = get_preconditions()

    def out():
        yield TITLE("Example: Get activity data for a patient using therapeut login")

        yield STEP("Preconditions")
        yield TXT("Authorized and IDs for organization and project is acquired. <a href='" + url_for(
            'api_doc_example2_view') + "'>Example</a>")

        yield STEP("List Patients")
        yield TXT("Get a list of all patients patient added to the project.")
        value, msg = api_get('/api/1.0/patients', {'org_id': org_id, 'project_id': proj_id}, token)
        yield API_CALL(msg)

        patient_id = value['value'][0]['patients'][0]['id']

        yield STEP("List the measurements of a Patient")
        yield TXT("Select the DEMO patient, and list measurements.")
        value, msg = api_get('/api/1.0/measurements', {'org_id': org_id, 'project_id': proj_id, 'patient_id': patient_id}, token)
        yield API_CALL(msg)

        measurement_id = value['value']['measurements'][0]['id']

        yield STEP("Activity Data - 24 H")
        yield TXT("Select a day in the measurement to get collected data.")
        value, msg = api_get('/api/1.0/measurement/data/derived',
                             {'org_id': org_id,
                              'project_id': proj_id,
                              'measurement_id': measurement_id,
                              'start_time': '2018-10-02T23:00:00',
                              'window_type': 'day',
                              'streams': 'person/activity'
                              }, token)
        yield API_CALL(msg)

    return out()


@app.route('/internal/docs/api_examples/4')
@api_demo_view
def api_doc_example4_view():

    token, org_id, proj_id = get_preconditions()

    def out():
        yield TITLE("Example: Get patient keys to allow patient access to data.")

        yield STEP("Preconditions")
        yield TXT("Authorized and IDs for organization and project is acquired. <a href='" + url_for('api_doc_example2_view') + "'>Example</a>")

        yield STEP("List Patients")
        yield TXT("Get a list of all patients patient added to the project.")
        value, msg = api_get('/api/1.0/patients', {'org_id': org_id, 'project_id': proj_id}, token)
        yield API_CALL(msg)

        patient_id = value['value'][0]['patients'][0]['id']

        yield STEP("Get the access keys for patient")
        yield TXT("Select the DEMO patient, and get the keys.")
        value, msg = api_get('/api/1.0/patient/get_keys', {'org_id': org_id, 'project_id': proj_id, 'patient_id': patient_id}, token)
        yield API_CALL(msg)

    return out()


@app.route('/internal/docs/api_examples/5')
@api_demo_view
def api_doc_example5_view():

    def out():
        yield TITLE("Example: Get activity data for a patient using patient keys.")

        yield STEP("Preconditions")
        yield TXT("Patients has the access keys. <a href='" + url_for('api_doc_example2_view') + "'>Example</a>")

        yield STEP("Activity Data - 24 H status - today")
        yield TXT("Get activity progress of today compared to current goals. Note, keys are used instead of an login+auth_token.")
        value, msg = api_get('/api/1.0/patient_view/progress',
                             {'project_key': 'xxx',
                              'patient_key': 'yyy'
                              }, None)
        yield API_CALL(msg)

        yield TXT("If ther is no active measurement for the patient, it cannot show status for today.")

        yield STEP("Activity Data - 24 H status - previous day")
        yield TXT("Get activity progress of today compared to current goals, but for a previous day.")
        value, msg = api_get('/api/1.0/patient_view/progress',
                             {'project_key': 'xxx',
                              'patient_key': 'yyy',
                              'date': '2018-12-21'
                              }, None)
        yield API_CALL(msg)

        yield STEP("Activity Data - 7 days status - previous day")
        yield TXT("Get activity progress of today compared to current goals, but for a previous day. Can show status for multiple days.")
        value, msg = api_get('/api/1.0/patient_view/progress',
                             {'project_key': 'xxx',
                              'patient_key': 'yyy',
                              'date': '2018-12-21',
                              'day_count': 7
                              }, None)
        yield API_CALL(msg)

    return out()

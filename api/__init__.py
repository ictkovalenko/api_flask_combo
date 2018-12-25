from api.error_codes import ApiStatus
from flaskapp import app
from flasgger import Swagger


swagger_config = {
    "title": "Tracking API v2.1.1-pre-2018-12-21",
    "headers": [
    ],
    "specs": [
        {
            "version": "2.1.1-pre",
            "endpoint": 'api_2_1_1',
            "route": '/api_2_1_1.json',
            "description":
                'REST API for tracking\n'
                '\n'
                '** WARNING: This API is unstable, and will most likely change. **\n'
                '\n'
                '** LAST UPDATE - 2018-12-21 **\n'
                '\n'
                'GET endpoints takes arguments in the query string.\n'
                'POST endpoints takes arguments in json format\n'
                '\n'
                'Reply format is always in json with the fields:\n'
                '```\n'
                '{\n'
                '  "status_code": 0,   // API_REPLY_CODE\n'
                '  "status_msg": "OK", // API_REPLY_MESSAGE\n'
                '  "value": { ... }    // Only available if status_code == 0\n'
                '}\n'
                '```\n'
                '\n'
                'HTTP status code:\n'
                '- 200 - Call was handled and status_code == 0\n'
                '- 400 - Invalid arguments\n'
                '- 401 - Invalid Auth-Token\n'
                '- 406 - Call was handled and status_code != 0\n'
                '\n'
                '\n'
                'List of status codes:\n'
                '\n'
                '| API_REPLY_CODE | API_REPLY_MESSAGE  | Description                         |\n'
                '| -------------  |--------------------| ------------------------------------|\n'
                '%s' % (''.join(['| %d              | %s                 | ...               |\n' % (i, ApiStatus.msg(i)) for i in ApiStatus._msg.keys()])) + ''
                '\n'
                '\n'
                '',
            "rule_filter": lambda rule: rule.endpoint.startswith('/api/1.0'),
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/internal/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs/"
}

swagger = Swagger(app, config=swagger_config)

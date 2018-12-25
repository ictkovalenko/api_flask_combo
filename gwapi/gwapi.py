from .gateway import *
from .discover import *
from .sensor import *
from .admin import *

from flaskapp import app
from flask_cors import CORS

#cors = CORS(app, resources={r"/gwapi/*": {"origins": "*"}})

"""
General return codes


200 OK
406 Not Acceptable

401 auth failed, refresh auth token
403 forbidden ?
404 endpoint not found
405 method not allowed

"""


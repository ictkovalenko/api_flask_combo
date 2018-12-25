from .auth import *
from .projects import *
from .sensors import *
from .patients import *
from .ex_patient_data_api import *
from .ex_export_dev import *
from .sensor_data import *
from .measurement_data_api import *
from .measurement_api import *
from .patient_view_api import *
from .users import *
from flasgger import Swagger

from flaskapp import app
from flask_cors import CORS

#cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

"""
General return codes


200 OK
406 Not Acceptable

401 auth failed, refresh auth token
403 forbidden ?
404 endpoint not found
405 method not allowed

"""


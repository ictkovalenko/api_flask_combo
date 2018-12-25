
class ApiStatus:

    STATUS_OK = 0
    STATUS_USER_NOT_FOUND = 1
    STATUS_INVALID_PASSWORD = 2
    STATUS_ORG_NOT_FOUND = 3
    STATUS_PROJECT_NOT_FOUND = 4
    STATUS_SENSOR_NOT_FOUND = 5
    STATUS_INVALID_PARAMETER = 6
    STATUS_UNSUPPORTED_VERSION = 7
    STATUS_DEVICE_NOT_FOUND = 8
    STATUS_MEASUREMENT_NOT_FOUND = 9
    STATUS_GENERATING_RESOURCE = 10
    STATUS_PROFILE_NOT_FOUND = 11
    STATUS_PATIENT_NOT_FOUND = 12
    STATUS_ANALYSIS_IN_PROGRESS = 13
    STATUS_WRONG_SNS_CODE = 14

    _msg = {STATUS_OK: 'OK',
            STATUS_USER_NOT_FOUND: 'User Not Found',
            STATUS_INVALID_PASSWORD: 'Invalid Password',
            STATUS_ORG_NOT_FOUND: 'Organization Not Found',
            STATUS_PROJECT_NOT_FOUND: 'Project Not Found',
            STATUS_SENSOR_NOT_FOUND: 'Sensor Not Found',
            STATUS_INVALID_PARAMETER: 'Invalid or Missing Parameter',
            STATUS_UNSUPPORTED_VERSION: 'Unsupported Version',
            STATUS_DEVICE_NOT_FOUND: 'Device not found',
            STATUS_MEASUREMENT_NOT_FOUND: 'Measurement not found',
            STATUS_GENERATING_RESOURCE: 'Generating Resource',
            STATUS_PROFILE_NOT_FOUND: 'Profile not found',
            STATUS_PATIENT_NOT_FOUND: 'Patient not found',
            STATUS_ANALYSIS_IN_PROGRESS: 'Analysis in progress',
            STATUS_WRONG_SNS_CODE: 'Wrong SNS code',
            }

    @classmethod
    def msg(cls, code):
        if code in cls._msg:
            return cls._msg[code]
        else:
            return "unknown"

from models import MotionDevice, SensorAccess, Session2
from query.structure.projects_query import check_arguments


# Unprotected
def fetch_sensor(sensor_id):
    sensor = MotionDevice.query.get(sensor_id)
    return sensor


# Protected
@check_arguments
def fetch_all_sensors_for_project(project, include_remote_details=False):
    sensors = project.all_sensors

    return sensors


@check_arguments
def fetch_sensor_from_id(sensor_id, project, extend=False):
    sensor = SensorAccess.query.get(sensor_id)

    if sensor is None:
        return None

    if sensor not in project.all_sensors:
        return None

    if extend:
        extend_sensors_remote_details([sensor])
        extend_sensor_measurements(sensor)

    return sensor


# unprotected
def extend_sensors_remote_details(sensors):
    remote_ids = [sensor.remote_id for sensor in sensors if not hasattr(sensor, 'remote_details')]
    if len(remote_ids) != 0:
        sensor_details = MotionDevice.query.filter(MotionDevice.id.in_(remote_ids))
        sensor_details_dict = {d.id: d for d in sensor_details}
        for s in sensors:
            if not hasattr(s, 'remote_details'):
                s.remote_details = sensor_details_dict[s.remote_id]


# unprotected
def extend_sensor_measurements(sensor):
    if hasattr(sensor, 'sessions'):
        return

    extend_sensors_remote_details([sensor])
    sessions = Session2.query.filter(Session2.motion_device_id == sensor.remote_details.id)

    sensor.sessions = sessions

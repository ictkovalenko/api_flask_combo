from models.structure.measurement import Measurement


def fetch_measurement(project, measurement_id):
    m = Measurement.query.get(measurement_id)
    if m is None or m.project_id != project.id:
        return None

    return m

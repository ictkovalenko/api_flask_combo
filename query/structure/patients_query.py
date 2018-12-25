from models import Patient, ProjectAccessKey, PatientAccessKey
from query.structure.projects_query import check_arguments


@check_arguments
def fetch_patients_from_project(project):
    patients = project.all_patients
    return patients

# Protected

@check_arguments
def fetch_patient_from_id(patient_id, project):
    patient = Patient.query.get(patient_id)

    if patient is None:
        return None

    if patient not in project.all_patients:
        return None

    return patient


def fetch_patient_from_key(proj_key, patient_key):
    project_key = ProjectAccessKey.query.filter(ProjectAccessKey.key_string == proj_key).first()

    if project_key is None:
        return None, None

    project = project_key.project
    patient_key = PatientAccessKey.query\
                                  .filter(PatientAccessKey.key_string == patient_key)\
                                  .filter(PatientAccessKey.project_id == project.id)\
                                  .first()

    if patient_key is None:
        return project, None
    else:
        return project, patient_key.patient

from flask import g
from flaskapp import app
from migrate import MSG
from migrate.migrate_db import migrate_create_structure_db
from migrate.migrate_measurement import migrate_measurements_from_patient_group, migrate_measurement, \
    migrate_patient, migrate_add_patient_key, migrate_add_measurement
from migrate.migrate_org import migrate_single_usergroup, migrate_add_single_organization, \
    migrate_add_project_key, migrate_single_usergroup_internally, migrate_add_new_project, migrate_add_project_to_org
from migrate.migrate_patients import migrate_add_new_patient
from migrate.migrate_profiles import migrate_add_alg_profile
from migrate.migrate_sensor import migrate_sensors, migrate_single_sensor
from migrate.migrate_user import migrate_single_user, migrate_add_user_to_project
from models import PatientProfile
from models.structure.measurement import AlgProfile
from models.structure.patient import create_patient_profiles
from utils import parse_date_string
from views.util import text_view


@app.route('/internal/migrate/1/create')
@text_view
def view_migrate_1_create():
    MSG("Starting")
    migrate_create_structure_db()
    return [""]


@app.route('/internal/migrate/1/basic')
@text_view
def view_migrate_1_basic():
    MSG("Starting")

    migrate_add_alg_profile(AlgProfile(name='generic/movement', algorithm='acc/movement', parameters='', hash=1))
    migrate_add_alg_profile(AlgProfile(name='person/activity', algorithm='person/activity', parameters='', hash=1))
    migrate_add_alg_profile(AlgProfile(name='person/activity2s', algorithm='person/activity2s', parameters='', hash=1))
    create_patient_profiles()


@app.route('/internal/migrate/1/sens')
@text_view
def view_migrate_1_sens():

    # Sens Testers

    migrate_single_user('s@polk.com')

    migrate_single_usergroup(name='sens-testers',
                             project_class='default')

    migrate_single_sensor(25, org_name='sens-testers', project_name='main')
    migrate_single_sensor(2251, org_name='sens-testers', project_name='main')
    # todo: create_new_project 100hz-test
    migrate_single_sensor(2095, org_name='sens-testers', project_name='100hz-test')
    migrate_single_sensor(2249, org_name='sens-testers', project_name='100hz-test')

    # SENSER-TESTING
    migrate_single_usergroup('sensor-testing', 'default')
    for sid in [2135, 50]:
        migrate_single_sensor(sid, org_name='sensor-testing', project_name='main')

    migrate_measurement('sensor-testing', 'main', 2617)

    migrate_add_new_project('sens-testers', 'sens-demo', 'default')
    migrate_single_sensor(2251, org_name='sens-testers', project_name='sens-demo')

    migrate_add_new_patient(org='sens-testers',
                            proj='sens-demo',
                            name='SENS Demo 2018-09',
                            profile='patient/default'
                            )

    migrate_add_measurement('sens-testers',
                            'sens-demo',
                            'SENS Demo 2018-09''',
                            '17-CF.FE',
                            parse_date_string('2018-09-27T07:00'),
                            parse_date_string('2018-10-08T16:00'))

    return g.msg


@app.route('/internal/migrate/1/new')
@text_view
def view_migrate_1_new():
    MSG("NEW")
    migrate_add_single_organization(org_name='new-projects',
                                    project_class='default')

    for s in [
        2463,
        2464,
        2465,
        2466,
        2467,
        2471
    ]:
        migrate_single_sensor(s, org_name='new-projects', project_name='main')

    return g.msg


@app.route('/internal/migrate/1/bb')
@text_view
def view_migrate_1_bb():
    migrate_single_usergroup(name='fys-ergo-bispebjerg',
                             project_class='hospital1')

    migrate_add_patient_profile(PatientProfile(short_name='patient/hospital/h1', meta='{"hospital_mobility": "h1"}'))
    migrate_add_patient_profile(PatientProfile(short_name='patient/hospital/h2', meta='{"hospital_mobility": "h2"}'))
    migrate_add_patient_profile(PatientProfile(short_name='patient/hospital/h3', meta='{"hospital_mobility": "h3"}'))

    migrate_measurements_from_patient_group('fys-ergo-bispebjerg', 'main', 64)  # BB Pretest Udskrevet

    return g.msg


@app.route('/internal/migrate/1/strathclyde')
@text_view
def view_migrate_1_strathclyde():
    migrate_single_usergroup(name='strathclyde',
                             project_class='default')

    for sid in [2118, 2119, 2120, 2121, 2122, 2123]:
        migrate_single_sensor(sid, 'strathclyde', 'main')

    migrate_single_user('jonathan.delafield-butt@strath.ac.uk')

    return g.msg


@app.route('/internal/migrate/1/intermedcon')
@text_view
def view_migrate_1_intermedcon():
    migrate_single_usergroup(name='intermedcon',
                             project_class='default')

    for sid in [2064, 2067]:
        migrate_single_sensor(sid, 'intermedcon', 'main')

    migrate_single_user('s@polk.com')
    migrate_add_user_to_project('s@polk.com', 'mmc', 'main')

    migrate_add_new_project('mmc', 'mmc-sandbox', 'default')
    migrate_add_user_to_project('s@polk.com', 'mmc', 'mmc-sandbox')

    migrate_add_project_to_org(org='mmc-testers', proj='mmc-demo', to_org='mmc')

    return g.msg


@app.route('/internal/migrate/1/dtu_app')
@text_view
def view_migrate_1_dtu_app():
    migrate_add_single_organization(org_name='dtu-app',
                                    project_class='default')

    m_sensor_id = 2251
    g4_sensor_id = 2253
    g5_sensor_id = 2255
    g6_sensor_id = 2252

    migrate_single_sensor(g4_sensor_id, org_name='dtu-app', project_name='main')
    migrate_single_sensor(g5_sensor_id, org_name='dtu-app', project_name='main')
    migrate_single_sensor(g6_sensor_id, org_name='dtu-app', project_name='main')
    migrate_single_sensor(m_sensor_id, org_name='dtu-app', project_name='main')

    migrate_patient(org_name='dtu-app',
                    proj_name='main',
                    mu_id=1644)

    migrate_add_project_key(org_name='dtu-app',
                            proj_name='main',
                            key='xxx')

    return g.msg


@app.route('/internal/migrate/1/any/<group_id>')
@text_view
def view_migrate_1_any(group_id):
    migrate_add_single_organization(org_name='pre-migrated',
                                    project_class='default')

    migrate_single_usergroup_internally(ug_id=group_id,
                                        project_class='default')

    return g.msg

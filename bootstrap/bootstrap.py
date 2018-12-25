import base64
import json
from flask import g
from flaskapp import app
from components import db
from migrate.migrate_profiles import migrate_add_alg_profile
from models import Organization, Project, PatientProfile, Patient, SensorPool, SensorAccess, MotionDevice, Session2, Stream2, \
    SensorRecord2, add_bin_data, TimeSync, CacheDerivedData, CacheQueueEntry
from models.structure.measurement import AlgProfile, Measurement, MeasurementSensor
from models.structure.user import User, UserGroup, UserGroupUserAssociation, shadow_pwd
from datetime import datetime
from sqlalchemy_utils import database_exists, create_database
from utils import parse_date_string


def MSG(txt):
    if not hasattr(g, 'msg'):
        g.msg = []
    g.msg += [txt]


def bootstrap_create_sensordata_db():
    db_url = db.get_engine(bind='sensordata').url
    if not database_exists(db_url):
        MSG("Creating Sensordata DB")
        create_database(db_url)

    MSG("Creating Sensordata Tables")
    db.create_all(bind='sensordata')


def bootstrap_create_structure_db():
    db_url = db.get_engine(bind='structure').url
    if not database_exists(db_url):
        MSG("Creating Structure DB")
        create_database(db_url)

    MSG("Deleting Tables")
    try:
        db.drop_all(bind='structure')
    except:
        MSG("Failed. Perhaps didn't exist")

    MSG("Creating Structure Tables")
    db.session()
    db.create_all(bind='structure')


def bootstrap_create_user(email, password):
    # Create test user
    email = u'api@gmail.com'
    u = User(email=email, password=shadow_pwd(email, u'secret'), password_time=datetime.utcnow())
    db.session.add(u)
    MSG("Created user " + u.email)
    return u


def bootstrap_create_org(short_name, name):
    org = Organization(short_name=short_name, name=name, member_group=UserGroup())
    db.session.add(org)
    MSG("Created org " + org.short_name)
    return org


def bootstrap_create_patient(short_name, description, project):
    patient = Patient(short_name=short_name, description=description, meta='', project=project)
    db.session.add(patient)
    db.session.commit()
    MSG("Created patient " + patient.short_name)
    return patient


def bootstrap_add_org_user(org, user):
    asso = UserGroupUserAssociation(level=1, user=user, group=org.member_group)
    db.session.add(asso)


def bootstrap_create_project(short_name, name):
    proj = Project(short_name=short_name, name=name, member_group=UserGroup(), created_time=datetime.utcnow())
    db.session.add(proj)
    db.session.commit()
    MSG("Created project " + proj.short_name)
    return proj


def bootstrap_add_org_project(org, proj):
    db.session.begin_nested()

    org.projects.append(proj)
    db.session.commit()


def bootstrap_add_project_patient(proj, patient):
    proj.append(patient)
    db.session.add()
    db.session.commit()


def bootstrap_add_project_user(proj, user):
    asso = UserGroupUserAssociation(level=1, user=user, group=proj.member_group)
    db.session.add(asso)


def bootstrap_create_sensor_device(mac, created_date=None):
    mac_int = MotionDevice.mac_int(mac)
    dev = MotionDevice.query.filter(MotionDevice.mac == mac_int).first()
    if dev is None:
        dev = MotionDevice(mac=mac_int, type=0x22, sensor_state=0, activated=1, last_seen=datetime.utcnow(), created_date=created_date)
        db.session.add(dev)
        db.session.commit()
    return dev


def bootstrap_create_sensor_access(remote_id, project):
    sensor_acc = SensorAccess(remote_id=remote_id, start_time=datetime(year=2017, day=1, month=1),
                              project=project)
    db.session.add(sensor_acc)
    return sensor_acc


def bootstrap_create_measurement(proj, start_time, patient, sensor):
    algprofile = AlgProfile.query.filter(AlgProfile.name == 'person/activity').first()
    m = Measurement(project=proj,
                    start_time=start_time,
                    end_time=None,
                    profile=algprofile,
                    parameters="",
                    state=Measurement.STATE_OPEN,
                    patient=patient)
    db.session.add(m)
    mSensor = MeasurementSensor(place='person/thigh',
                                parameters='',
                                sensor_id=sensor.id,
                                measurement=m,
                                sensor=sensor)
    db.session.add(mSensor)
    db.session.commit()


def bootstrap_import_session2_legacy(filename, sensor):
    if app.config['ALLOW_BOOTSTRAP'] is not True:
        print("Bootstrap Not Allowed")
        return

    with open(filename, 'r') as infile:
        imported = json.load(infile)

        # Create Session2
        d = imported['session']

        if Session2.query.filter(Session2.motion_device==sensor).filter(Session2.start_time==parse_date_string(d['start_time'])).count() != 0:
            return

        s2 = Session2(created=parse_date_string(d['created']),
                      start_time=parse_date_string(d['start_time']),
                      end_time=parse_date_string(d['end_time']),
                      motion_device=sensor,
                      closed=d['closed'],
                      deleted=d['deleted'])

        db.session.add(s2)
        db.session.commit()

        for ts in imported['session']['timesyncs']:
            ts = TimeSync(session_id=s2.id,
                          timestamp_tx=ts['timestamp_tx'],
                          server_time=parse_date_string(ts['server_time']))
            db.session.add(ts)

        for d in imported['session']['streams']:
            st = Stream2(stream_type=d['stream_type'],
                         data_format=d['data_format'],
                         last_record_added_tx=d['last_record_added_tx'],
                         open_record_tx=d['open_record_tx'],
                         properties=d['properties'],
                         session=s2)
            db.session.add(st)
            db.session.commit()

            for rd in d['records']:
                bindata = base64.decodebytes(bytes(rd['bindata'], 'ascii'))
                rec = SensorRecord2(stream_id=st.id,
                                    timestamp_tx=rd['timestamp_tx'],
                                    timestamp_tx_end=rd['timestamp_tx_end'],
                                    stream_cnt_begin=rd['stream_cnt_begin'],
                                    stream_cnt_end=rd['stream_cnt_end'],
                                    datastore=0
                                    )
                db.session.add(rec)
                add_bin_data(rec, bindata)
        MSG("Session loaded")

        db.session.commit()


def bootstrap_import_session2(filename, sensor):
    if app.config['ALLOW_BOOTSTRAP'] is not True:
        print("Bootstrap Not Allowed")
        return

    with open(filename, 'r') as infile:
        imported = json.load(infile)

        # Create Session2
        d = imported['session']

        if Session2.query.filter(Session2.motion_device==sensor).filter(Session2.start_time==parse_date_string(d['start_time'])).count() != 0:
            return

        s2 = Session2(created=parse_date_string(d['created']),
                      start_time=parse_date_string(d['start_time']),
                      end_time=parse_date_string(d['end_time']),
                      motion_device=sensor,
                      closed=d['closed'],
                      deleted=d['deleted'])

        db.session.add(s2)
        db.session.commit()

        for ts in imported['session']['timesyncs']:
            ts = TimeSync(session_id=s2.id,
                          timestamp_tx=ts['timestamp_tx'],
                          server_time=parse_date_string(ts['server_time']))
            db.session.add(ts)

        for d in imported['session']['streams']:
            st = Stream2(stream_type=d['stream_type'],
                         data_format=d['data_format'],
                         last_record_added_tx=d['last_record_added_tx'],
                         open_record_tx=d['open_record_tx'],
                         properties=d['properties'],
                         session=s2)
            db.session.add(st)
            db.session.commit()

            for rd in d['records']:
                bindata = base64.decodebytes(bytes(rd['bindata'], 'ascii'))
                rec = SensorRecord2(stream_id=st.id,
                                    timestamp_tx=rd['timestamp_tx'],
                                    timestamp_tx_end=rd['timestamp_tx_end'],
                                    stream_cnt_begin=rd['stream_cnt_begin'],
                                    stream_cnt_end=rd['stream_cnt_end'],
                                    datastore=0
                                    )
                db.session.add(rec)
                add_bin_data(rec, bindata)
        db.session.commit()


def bootstrap_local_test():
    if app.config['ALLOW_BOOTSTRAP'] is True:

        bootstrap_create_structure_db()
        bootstrap_create_sensordata_db()

        migrate_add_alg_profile(
            AlgProfile(name='generic/movement', algorithm='activity_movement', parameters='', hash=1))
        migrate_add_alg_profile(AlgProfile(name='person/activity', algorithm='person/activity', parameters='', hash=1))

        u = bootstrap_create_user(email=u'api@gmail.com', password=u'secret')

        ############################
        # Create test organization 1

        org = bootstrap_create_org(short_name='sens-innovation', name='MMO pol')
        bootstrap_add_org_user(org=org, user=u)

        # Create test project 1-1
        proj = bootstrap_create_project(short_name='internal-1', name='Internal Activity Tests 1')
        bootstrap_add_project_user(proj, u)
        bootstrap_add_org_project(org, proj)
        patient1 = bootstrap_create_patient(short_name='mile', description='mmop', project=proj)
        bootstrap_create_patient(short_name='GHOST', description='gols', project=proj)

        sensor1 = bootstrap_create_sensor_device(mac='AA:BB:CC:DD:EE:FF')
        bootstrap_create_sensor_access(remote_id=sensor1.id, project=proj)

        sensor2 = bootstrap_create_sensor_device(mac='BB:BB:CC:DD:EE:BB')
        bootstrap_create_sensor_access(remote_id=sensor2.id, project=proj)

        sensor3 = bootstrap_create_sensor_device(mac='CC:CC:CC:DD:EE:AA')
        bootstrap_create_sensor_access(remote_id=sensor3.id, project=proj)

        sensor4 = bootstrap_create_sensor_device(mac='DD:DD:CC:DD:EE:FF')
        bootstrap_create_sensor_access(remote_id=sensor4.id, project=proj)

        sensor5 = bootstrap_create_sensor_device(mac='EE:EE:CC:DD:EE:DD')
        bootstrap_create_sensor_access(remote_id=sensor5.id, project=proj)

        sensor6 = bootstrap_create_sensor_device(mac='FF:FF:CC:DD:EE:CC')
        bootstrap_create_sensor_access(remote_id=sensor6.id, project=proj)

        db.session.commit()

        # Import some data
        bootstrap_import_session2_legacy('../source/session_export_2018_12_21.json', sensor1)

        # Import Morten Test Data
        sensor7 = bootstrap_create_sensor_device(mac='F8:80:20:08:FF:FA')
        sa = bootstrap_create_sensor_access(remote_id=sensor7.id, project=proj)

        bootstrap_import_session2('./test_data/exported_session_2018-12-21.json', sensor7)
        bootstrap_create_measurement(proj,datetime(2018, 10, 1),patient1, sa)
        print("Measurement started")
        # Create test project 1-2
        proj = bootstrap_create_project(short_name='hw-test-1', name='Hardware Revision Tests')
        bootstrap_add_project_user(proj, u)
        bootstrap_add_org_project(org, proj)

        ############################
        # Create test organization 2

        org = bootstrap_create_org(short_name='SAT', name='SAT')
        bootstrap_add_org_user(org=org, user=u)

        # Create test project 2-1
        proj = bootstrap_create_project(short_name='mmp-kbp-1', name='MMP KBP 2018')
        bootstrap_add_project_user(proj, u)
        bootstrap_add_org_project(org, proj)
        bootstrap_create_patient(short_name='JJM', description='Cuna', project=proj)

        # Create test project 2-2
        proj = bootstrap_create_project(short_name='mmp-kbp-2', name='MMP KBP 2018')
        bootstrap_add_project_user(proj, u)
        bootstrap_add_org_project(org, proj)

        # Create test project 2-3
        proj = bootstrap_create_project(short_name='mmp-kbp-3', name='MMP KBP 2018')
        bootstrap_add_project_user(proj, u)
        bootstrap_add_org_project(org, proj)

        db.session.commit()

        CacheDerivedData.query.delete()
        CacheQueueEntry.query.delete()

        return True

    else:
        MSG("Not Testing Config")
        return False



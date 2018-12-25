from flask import g
from bootstrap import bootstrap
from components import db
from flaskapp import app
from migrate import MSG
from models import GatewayDevice, GatewayScanReport, GatewaySensorDiscovered, GatewaySensorActionRequest, \
    Project, Organization, SensorAccess, SensorPool
from views.util import text_view
from sqlalchemy.schema import CreateTable

# Migrate
# Create table GatewaySensorActionRequest
#
# Alter table gateway_seen_device - gateway_seen_device.action_request_id - INTEGER
#
# Alter table 'gateway_devices.parameters' VARCHAR(4048),
# last_report_id = db.Column(db.Integer
#
# gateway_scan_report.meta varchar 2048


@app.route('/internal/bootstrap_local_test')
@text_view
def bootstrap2_view():
    """
    Bootstrap Local Test Databse
    """
    MSG("START BOOTSTRAP")
    bootstrap.bootstrap_local_test()
    return g.msg


@app.route('/internal/bootstrap_structure')
@text_view
def bootstrap_view():
    """
    Bootstrap Empty Structure DB for migrating
    """
    MSG("START BOOTSTRAP")
    db.create_all(bind='structure')
    return g.msg


@app.route('/internal/db')
@text_view
def db_view():

    def out():
        yield "DB SensorData"

        for t in [GatewayDevice, GatewayScanReport, GatewaySensorDiscovered, GatewaySensorActionRequest]:
            yield ""
            try:
                yield "----------"
                yield str(t.__tablename__)
                yield ""
                q = t.query.first()
                yield "Query: OK"
            except Exception as e:
                yield "Query: FAIL"
                yield str(e)
                yield ""
                yield str(CreateTable(t.__table__))

    return out()


@app.route('/internal/db2')
@text_view
def db2_view():

    def out():
        yield "DB Structure"

        for t in [Organization, Project, SensorAccess, SensorPool]:
            yield ""
            try:
                yield "--------------------"
                yield str(t.__tablename__)
                yield "--------------------"
                q = t.query.first()
                yield "Get First: OK"
                for x in dir(q):
                    if not x.startswith('_'):
                        try:
                            getattr(q, x)
                        except Exception as e:
                            yield str(e)
            except Exception as e:
                yield "Query: FAIL"
                yield str(e)
                yield ""
                yield str(CreateTable(t.__table__))

    return out()

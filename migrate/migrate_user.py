from datetime import datetime
from components import db
from flaskapp import app
from migrate import MSG
from migrate.migrate_org import migrate_find_project2
from models.legacy import UserInfo
from models.structure.user import User, UserGroup, UserGroupUserAssociation


def migrate_single_user(email):
    if not app.config['ALLOW_MIGRATE'] is True:
        return

    MSG("Migrating User %s" % email)

    user_old = UserInfo.query.filter(UserInfo.username==email).first()

    user = User.query.filter(User.email == email).first()

    if user:
        MSG("- Exists")
        user.password = user_old.password
        db.session.commit()
        return

    user = User(email=user_old.email, password=user_old.password, password_time=datetime.utcnow())
    db.session.add(user)
    db.session.commit()

    MSG("- Added")

    db.session.commit()

    MSG("- OK %s" % email)


def migrate_add_user_to_project(email, org_name, proj_name):

    org, proj = migrate_find_project2(org_name, proj_name)

    user = User.query.filter(User.email==email).first()

    if not org.member_group.has_user(user):
        db.session.add(UserGroupUserAssociation(user=user, group=org.member_group, level=0))
    if not proj.member_group.has_user(user):
        db.session.add(UserGroupUserAssociation(user=user, group=proj.member_group, level=0))

    db.session.commit()

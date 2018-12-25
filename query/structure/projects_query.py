from sqlalchemy.orm import joinedload
from models import Organization, Project, PatientProfile, Patient
from functools import wraps


def check_arguments(func):
    @wraps(func)
    def with_check(*args, **kwargs):
        for i, a in enumerate(args):
            if a is None:
                raise ValueError("Argument #%d is None", i)
        return func(*args, **kwargs)
    return with_check


# Protected
@check_arguments
def fetch_all_orgs_for_user(user, include_projects=False):

    # Unrestricted check
    if user.is_unrestricted():
        if include_projects:
            orgs = Organization.query. \
                options(joinedload(Organization.projects)). \
                all()
        else:
            orgs = Organization.query. \
                all()

        return orgs

    # Normal
    ug_ids = [a.group.id for a in user.user_groups]

    if include_projects:
        orgs = Organization.query.\
            filter(Organization.member_group_id.in_(ug_ids)).\
            options(joinedload(Organization.projects)).\
            all()
    else:
        orgs = Organization.query.\
            filter(Organization.member_group_id.in_(ug_ids)).\
            all()
    return orgs


# Protected
@check_arguments
def fetch_org_and_project(user, org_id, proj_id):
    ug_ids = [a.group.id for a in user.user_groups]

    # todo: candidate for optimization
    #org = Organization.query.filter(Organization.id == org_id).filter(Organization.member_group_id.in_(ug_ids)).first()
    org = Organization.query.filter(Organization.id == org_id).first()

    if org is None:
        return None, None
    else:
        proj = Project.query.filter(Project.id == proj_id).first()#filter(Project.member_group_id.in_(ug_ids)).first()
        if proj is None or proj.id not in [p.id for p in org.projects]:
            return org, None
        return org, proj

# Protected

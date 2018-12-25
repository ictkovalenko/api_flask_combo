from sqlalchemy import MetaData
from components import db
from flaskapp import app
from migrate import MSG

"""
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE 'spam'.'eggs';
SET FOREIGN_KEY_CHECKS = 1;
"""

def migrate_create_structure_db():
    if not app.config['ALLOW_MIGRATE'] is True:
        return

    #MSG("Deleting Struct Table")
    #try:
    #    db.drop_all(bind='structure')
    #except Exception as e:
    #    print(e)
    #    MSG("Failed. Perhaps didn't exist")

    MSG("Creating Table - structure db")
    db.create_all(bind='structure')


from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

from . import config

engine = None

# I don't want name to be lower (default will return name.lower())
def name_for_scalar_relationship(base, local_cls, referred_cls, constraint):
    if local_cls.__table__.name == 'Song':
        if constraint.columns[0] == 'author': return 'Author'
        if constraint.columns[0] == 'last_author': return 'LastAuthor'
    if local_cls.__table__.name == 'Comment':
        if constraint.columns[0] == 'author': return 'Author'
    return referred_cls.__name__

def name_for_collection_relationship(base, local_cls, referred_cls, constraint):
    if referred_cls.__table__.name == 'Song':
        if constraint.columns[0] == 'author': return 'Song_Author_collection'
        if constraint.columns[0] == 'last_author': return 'Song_LastAuthor_collection'
    return referred_cls.__name__ + '_collection'



def connect(db_name):
    global engine
    engine = create_engine('mysql+mysqlconnector://{USER}:{PASS}@{HOST}/{DB_NAME}'.format(
        USER=config.USER, PASS=config.PASS, HOST=config.HOST, DB_NAME=db_name,
    ), pool_recycle=3600)

    base = automap_base()
    base.prepare(engine, reflect=True,
                name_for_scalar_relationship=name_for_scalar_relationship,
                name_for_collection_relationship=name_for_collection_relationship)
    globals().update(dict(base.classes))

    # don't know why but need this line to create "db.<table>.*_collection"
    base.classes.values()[0].__mapper__.relationships


def get_session():
    if not engine: raise Exception('You should run db.connect(db_name) first.')
    return Session(engine)

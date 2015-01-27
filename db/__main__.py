#!/usr/bin/env python3
"""
reset/init db with `python -m db <db_name>`

same as: `./initdb.py python <db_name> < schema.in | python && ./default_val <db_name>`
"""
import sys
import os.path

import db

def get_res_path(path):
    return os.path.join(os.path.dirname(__file__), path)

SCHEMA_PATH = get_res_path('schema.in')


#################### routings ####################
def init(db_name):
    print('parsing schema.in...')
    from . import initdb
    output = initdb.main('python', db_name, open(SCHEMA_PATH).read())

    print('creating db schema...')
    exec(compile(output, '<string>', 'exec'), {})

    print('calling default_val.insert_default()...')
    from . import default_val
    default_val.insert_default(db_name)


if __name__ == '__main__':
    try:
        db_name = sys.argv[1]
    except IndexError:
        print('Usage: %s <db_name>' % sys.argv[0])
        exit(1)

    ans = input('Are you sure want to reset %s? [Y/n]: ' % db_name)
    if ans.lower() in ('n', 'no'):
        print('db not changed.')
    else:
        init(db_name)
        print('done.')


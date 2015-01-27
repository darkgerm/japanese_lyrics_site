#!/usr/bin/env python3
import sys
import collections

import db

def insert_default(db_name):
 print('[default_val] preparing for db...')
 db.connect(db_name)

 print('[default_val] preparing for values...')
 val = collections.OrderedDict()

 # add something into val here.

 print('[default_val] insearting values...')
 session = db.get_session()
 session.add_all(val.values())
 session.commit()


if __name__ == '__main__':
 if len(sys.argv) <= 1:
  print('Usage: %s db_name' % sys.argv[0])
  exit(1)
 insert_default(sys.argv[1])

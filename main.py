#!/usr/bin/env python3

from functools import wraps
from datetime import datetime

from flask import Flask
from flask import redirect
from flask import url_for
from flask import session
from flask import request
from flask import jsonify
from flask import render_template
from flask import g
from flask_oauthlib.client import OAuth

import config
import db
db.connect(config.DB_NAME)


#################### flask app instance ####################
app = Flask(__name__)
app.debug = config.DEBUG
app.secret_key = config.SERVER_SECRET_KEY
app_param = {
    'host': config.HOST,
    'port': config.PORT,
    'threaded': True,
}


#################### db relative ####################
@app.before_request
def before_request():
    g.db_session = db.get_session()

@app.teardown_request
def teardown_request(exception):
    db_session = getattr(g, 'db_session', None)
    if db_session is not None:
        db_session.close()

def db_save_user(email, name, picture):
    '''save to User and return u_id'''
    user = g.db_session.query(db.User).filter(db.User.email==email).first()
    if not user:
        # user not exist, new one
        user = db.User(email=email, name=name, picture=picture)
        g.db_session.add(user)
    else:
        # update user info
        user.name, user.picture = name, picture
    g.db_session.commit()
    return user.u_id


def db_query_cmts(s_id):
    '''query all cmts. s_id: None means global'''
    query_cmts = g.db_session.query(db.Comment).filter(db.Comment.s_id==s_id)
    cmts = []
    for cmt in query_cmts:
        cmts.append({
            'author': cmt.Author.name.decode(),
            'author_picture': cmt.Author.picture.decode(),
            'time': cmt.time.strftime('%Y-%m-%d %H:%M:%S'),
            'content': cmt.content.decode(),
        })
    return cmts[::-1]


#################### Google OAuth2 ####################
oauth = OAuth(app)

google = oauth.remote_app(
    'google',
    consumer_key = config.GOOGLE_ID,
    consumer_secret = config.GOOGLE_SECRET,
    request_token_params = {
        'scope': 'https://www.googleapis.com/auth/userinfo.email'
    },
    base_url = 'https://www.googleapis.com/oauth2/v1/',
    request_token_url = None,
    access_token_method = 'POST',
    access_token_url = 'https://accounts.google.com/o/oauth2/token',
    authorize_url = 'https://accounts.google.com/o/oauth2/auth',
)


@app.route('/login_with_google')
def login_with_google():
    return google.authorize(callback=url_for('authorized', _external=True))


@app.route('/login/authorized')
def authorized():
    resp = google.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['google_token'] = (resp['access_token'], '')
    session['logged_in'] = True

    # check the user is in ALLOW_USER or not.
    me = google.get('userinfo')
    if me.data['email'] not in config.ALLOW_USER:
        session.pop('google_token', None)
        session.pop('logged_in', None)
        return render_template('permission_deny.html')

    # get additional information and save to session.
    # although it can get from db, it's for efficiency and convenience.
    session['google_picture'] = me.data['picture']
    session['google_name'] = me.data['name']

    # save user info to database
    u_id = db_save_user(me.data['email'], me.data['name'], me.data['picture'])
    session['u_id'] = u_id

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('google_token', None)
    session.pop('logged_in', None)
    return redirect(url_for('index'))


@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')


def login_required(func):
    '''If haven't login, back to index.'''
    @wraps(func)
    def wrapped(*args, **kwargs):
        if session.get('logged_in'):
            return func(*args, **kwargs)
        else:
            return redirect(url_for('index'))
    return wrapped


@app.route('/google_userinfo')
@login_required
def google_userinfo():
    if session.get('logged_in'):
        me = google.get('userinfo')
        return jsonify({"data": me.data})
    else:
        return 'you havent login.'


#################### route ####################
@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('song_list'))
    else:
        return render_template('index.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/song_list')
@login_required
def song_list():
    songs = []
    for song in g.db_session.query(db.Song):
        songs.append([
            '<a href="/view/%s">%s</a>' % (song.s_id, song.name.decode()),
            song.artist.decode(),
            song.origin.decode(),
            song.last_time.strftime('%Y-%m-%d %H:%M:%S'),
        ])
    cmts = db_query_cmts(None)
    return render_template('song_list.html', songs=songs, cmts=cmts)

@app.route('/view/<song_id>')
@login_required
def song_view(song_id):
    song_db = g.db_session.query(db.Song).filter(db.Song.s_id==song_id).first()
    song = {
        's_id': song_db.s_id,
        'name': song_db.name.decode(),
        'artist': song_db.artist.decode(),
        'origin': song_db.origin.decode(),
        'author': '%s (%s)' % (song_db.Author.name.decode(),
                               song_db.time.strftime('%Y-%m-%d %H:%M:%S')),
        'last_author': '%s (%s)' % (song_db.LastAuthor.name.decode(),
                                    song_db.last_time.strftime('%Y-%m-%d %H:%M:%S')),
        'lyrics': song_db.lyrics.decode(),
    }
    cmts = db_query_cmts(song_id)
    return render_template('song_view.html', song=song, cmts=cmts)

@app.route('/new')
@login_required
def song_new():
    return render_template('song_edit.html', new=True)

@app.route('/edit/<song_id>')
@login_required
def song_edit(song_id):
    song_db = g.db_session.query(db.Song).filter(db.Song.s_id==song_id).first()
    song = {
        's_id': song_db.s_id,
        'name': song_db.name.decode(),
        'artist': song_db.artist.decode(),
        'origin': song_db.origin.decode(),
        'lyrics': song_db.lyrics.decode(),
    }
    return render_template('song_edit.html', new=False, song=song)


@app.route('/save', methods=['POST'])
@login_required
def song_save():
    if not request.form['name'].strip():    # empty
        return redirect(url_for('song_list'))

    if request.form['new'] == 'True':
        new_song = db.Song(
            name = request.form['name'],
            artist = request.form['artist'],
            origin = request.form['origin'],
            lyrics = request.form['lyrics'],
            author = session['u_id'],
            time = datetime.today(),
            last_author = session['u_id'],
            last_time = datetime.today(),
        )
        g.db_session.add(new_song)
    else:
        s_id = request.form['s_id']
        song = g.db_session.query(db.Song).filter(db.Song.s_id==s_id).first()
        song.name = request.form['name']
        song.artist = request.form['artist']
        song.origin = request.form['origin']
        song.lyrics = request.form['lyrics']
        song.last_author = session['u_id']
        song.last_time = datetime.today()

    g.db_session.commit()
    return redirect(url_for('song_list'))


@app.route('/save_comment', methods=['POST'])
@login_required
def save_comment():
    if not request.form['content'].strip():     # empty
        return redirect(request.form['path'])

    s_id = int(request.form['s_id'])
    new_cmt = db.Comment(
        s_id = None if s_id == -1 else s_id,
        author = session['u_id'],
        time = datetime.today(),
        content = request.form['content'],
    )
    g.db_session.add(new_cmt)
    g.db_session.commit()
    return redirect(request.form['path'])


#################### main ####################
if __name__ == '__main__':
    app.run(**app_param)


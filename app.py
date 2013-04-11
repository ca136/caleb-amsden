#from gevent import monkey; monkey.patch_all()

from flask import Flask, url_for, redirect, render_template, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext import admin, login, wtf
from flask.ext.admin.contrib import sqlamodel
from flask.ext.admin.contrib.fileadmin import FileAdmin

#from socketio import socketio_manage
#from socketio.namespace import BaseNamespace
#from socketio.mixins import RoomsMixin, BroadcastMixin

import os.path as op
import re
from unicodedata import normalize
from datetime import datetime

# Create application
app = Flask(__name__)

# Create dummy secrey key so we can use sessions
app.config['SECRET_KEY'] = '123456790'

# Create in-memory database
app.config.from_object('config')

db = SQLAlchemy(app)

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:+]+')
def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))


# Create user model. For simplicity, it will store passwords in plain text.
# Obviously that's not right thing to do in real world application.
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    password = db.Column(db.String(64))

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    headline = db.Column(db.String(64), unique=True)
    body = db.Column(db.Text)
    pub_date = db.Column(db.DateTime)

    def __init__(self, headline, body, pub_date=None):
        self.headline = headline
        self.body = body
        if pub_date is None:
            pub_date = datetime.utcnow()
        self.pub_date = pub_date


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    headline = db.Column(db.String(64), unique=True)
    abstract = db.Column(db.Text)
    body = db.Column(db.Text)
    pub_date = db.Column(db.DateTime)

    def get_url(self):
        return '/article/{0}/{1}/'.format(self.id,\
                slugify(self.headline))


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), unique=True)
    main_photo = db.Column(db.Boolean)


# Define login and registration forms (for flask-login)
class LoginForm(wtf.Form):
    login = wtf.TextField(validators=[wtf.required()])
    password = wtf.PasswordField(validators=[wtf.required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise wtf.ValidationError('Invalid user')

        if user.password != self.password.data:
            raise wtf.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(User).filter_by(\
                login=self.login.data).first()


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.setup_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)

# Create customized model view class
class MyModelView(sqlamodel.ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated()


# Create customized index view class
class MyAdminIndexView(admin.AdminIndexView):
    def is_accessible(self):
        return login.current_user.is_authenticated()

# Render custom index for admin
class MyView(admin.BaseView):
    @admin.expose('/')
    def index(self):
        return self.render('index.html')

@app.route('/')
def index():
    notes = Note.query.all()
    return render_template('index.html', user=login.current_user,\
            notes=notes)

@app.route('/about/')
def about():
    return render_template('about.html', user=login.current_user)

@app.route('/articles/')
def articles():
    notes = Note.query.all()
    return render_template('articles.html', user=login.current_user,\
            notes=notes)

@app.route('/article/<path:article_path>/')
def article(article_path):
    article_id = article_path.split('/')[0]
    note = Note.query.get(article_id)
    related = Note.query.filter(Note.id != note.id)
    return render_template('article.html', user=login.current_user,\
            note=note, related=related)

@app.route('/login/', methods=('GET', 'POST'))
def login_view():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = form.get_user()
        login.login_user(user)
        return redirect(url_for('index'))

    return render_template('form.html', form=form)

@app.route('/register/', methods=('GET', 'POST'))
def register_view():
    form = RegistrationForm(request.form)
    if form.validate_on_submit():
        user = User()

        form.populate_obj(user)

        db.session.add(user)
        db.session.commit()

        login.login_user(user)
        return redirect(url_for('index'))

    return render_template('form.html', form=form)

@app.route('/logout/')
def logout_view():
    login.logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Initialize flask-login
    init_login()

    # Create admin
    admin = admin.Admin(app, 'Website', index_view=MyAdminIndexView())
    path = op.join(op.dirname(__file__), 'files')

    # Add views
    admin.add_view(FileAdmin(path, '/files/', name='Files'))
    admin.add_view(sqlamodel.ModelView(User, db.session))
    admin.add_view(sqlamodel.ModelView(Note, db.session))
    #admin.add_view(ProductAdmin(Product, db.session))

    # Create DB
    db.create_all()

    # Start app
    app.debug = True
    app.run()


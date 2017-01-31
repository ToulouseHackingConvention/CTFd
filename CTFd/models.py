import collections
import datetime
import hashlib
import json
from socket import inet_aton, inet_ntoa
from struct import unpack, pack, error as struct_error

from flask_sqlalchemy import SQLAlchemy
from passlib.hash import bcrypt_sha256
from sqlalchemy.exc import DatabaseError


def get_solves_and_value(is_admin=False):
    """Generator to get all the solves/awards.

    Args:
        is_admin: Whether the user is an admin or not. If not, we ignore
            the teams that are banned.

    Yields:
        Couples (solve, value).
        Where solve can be either a Solves model, or an Awards model.
        Value is an integer with the value for that solve/award, including
        eventual bonuses.
        It is wrong to assume that they are ordered by time (we start from
        the beginning again, for awards).
    """
    solves = db.session.query(Solves).join(Challenges) \
        .order_by(Solves.chalid, Solves.date)
    if not is_admin:
        solves = solves.filter(Teams.banned == False)

    current_chal_id = None
    current_chal_solves = 0
    for solve in solves:
        if solve.chalid != current_chal_id:
            current_chal_id = solve.chalid
            current_chal_solves = 1
        else:
            current_chal_solves += 1

        bonus = max(4 - current_chal_solves, 0)
        yield (solve, solve.chal.value + bonus)

    # Let's not forget to yield the awards too.
    awards = db.session.query(Awards).order_by(Awards.date)
    if not is_admin:
        awards = awards.filter(Teams.banned == False)
    for award in awards:
        yield (award, award.value)


def score_by_team(is_admin=False):
    score_by_team = collections.Counter()
    for solve, value in get_solves_and_value(is_admin=is_admin):
        score_by_team[solve.team] += value
    return score_by_team


def sha512(string):
    return hashlib.sha512(string).hexdigest()


def ip2long(ip):
    return unpack('!i', inet_aton(ip))[0]


def long2ip(ip_int):
    try:
        return inet_ntoa(pack('!i', ip_int))
    except struct_error:
        # Backwards compatibility with old CTFd databases
        return inet_ntoa(pack('!I', ip_int))


db = SQLAlchemy()


class Pages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route = db.Column(db.String(80), unique=True)
    html = db.Column(db.Text)

    def __init__(self, route, html):
        self.route = route
        self.html = html

    def __repr__(self):
        return "<Pages {0} for challenge {1}>".format(self.tag, self.chal)


class Containers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    buildfile = db.Column(db.Text)

    def __init__(self, name, buildfile):
        self.name = name
        self.buildfile = buildfile

    def __repr__(self):
        return "<Container ID:(0) {1}>".format(self.id, self.name)


class Challenges(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    description = db.Column(db.Text)
    value = db.Column(db.Integer)
    category = db.Column(db.String(80))
    flags = db.Column(db.Text)
    hidden = db.Column(db.Boolean, default=False)
    down = db.Column(db.Boolean, default=False)

    def __init__(self, name, description, value, category, flags):
        self.name = name
        self.description = description
        self.value = value
        self.category = category
        self.flags = json.dumps(flags)

    def __repr__(self):
        return '<chal %r>' % self.name


class Awards(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teamid = db.Column(db.Integer, db.ForeignKey('teams.id'))
    name = db.Column(db.String(80))
    description = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    value = db.Column(db.Integer)
    category = db.Column(db.String(80))
    icon = db.Column(db.Text)
    team = db.relationship('Teams', foreign_keys="Awards.teamid", lazy='joined')

    def __init__(self, teamid, name, value):
        self.teamid = teamid
        self.name = name
        self.value = value

    def __repr__(self):
        return '<award %r>' % self.name


class Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chal = db.Column(db.Integer, db.ForeignKey('challenges.id'))
    tag = db.Column(db.String(80))

    def __init__(self, chal, tag):
        self.chal = chal
        self.tag = tag

    def __repr__(self):
        return "<Tag {0} for challenge {1}>".format(self.tag, self.chal)


class Files(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chal = db.Column(db.Integer, db.ForeignKey('challenges.id'))
    location = db.Column(db.Text)

    def __init__(self, chal, location):
        self.chal = chal
        self.location = location

    def __repr__(self):
        return "<File {0} for challenge {1}>".format(self.location, self.chal)


class Keys(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chal = db.Column(db.Integer, db.ForeignKey('challenges.id'))
    key_type = db.Column(db.Integer)
    flag = db.Column(db.Text)

    def __init__(self, chal, flag, key_type):
        self.chal = chal
        self.flag = flag
        self.key_type = key_type

    def __repr__(self):
        return self.flag


class Teams(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True)
    email = db.Column(db.String(128), unique=True)
    password = db.Column(db.String(128))
    website = db.Column(db.String(128))
    affiliation = db.Column(db.String(128))
    country = db.Column(db.String(32))
    bracket = db.Column(db.String(32))
    banned = db.Column(db.Boolean, default=False)
    verified = db.Column(db.Boolean, default=False)
    admin = db.Column(db.Boolean, default=False)
    joined = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, name, email, password, website='', affiliation='', country=''):
        self.name = name
        self.email = email
        self.password = bcrypt_sha256.encrypt(str(password))
        self.website = website
        self.affiliation = affiliation
        self.country = country

    def __repr__(self):
        return '<team %r>' % self.name

    def score(self):
        """Score for the team, dynamically computed."""
        return score_by_team()[self]

    def place(self):
        """A string with the ranking of the team.

        Example: "1st", "3rd"...
        """
        def place_to_str(i):
            # http://codegolf.stackexchange.com/a/4712
            k = i % 10
            return '%d%s' % (i, 'tsnrhtdd'[(i / 10 % 10 != 1) * (k < 4) * k::4])

        for place, (team, score) in enumerate(score_by_team().most_common()):
            if self.id == team.id:
                return place_to_str(place + 1)

        return '0'  # team is banned, or other error.


class Solves(db.Model):
    __table_args__ = (db.UniqueConstraint('chalid', 'teamid'), {})
    id = db.Column(db.Integer, primary_key=True)
    chalid = db.Column(db.Integer, db.ForeignKey('challenges.id'))
    teamid = db.Column(db.Integer, db.ForeignKey('teams.id'))
    ip = db.Column(db.Integer)
    flag = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    team = db.relationship('Teams', foreign_keys="Solves.teamid", lazy='joined')
    chal = db.relationship('Challenges', foreign_keys="Solves.chalid", lazy='joined')
    # value = db.Column(db.Integer)

    def __init__(self, chalid, teamid, ip, flag):
        self.ip = ip2long(ip)
        self.chalid = chalid
        self.teamid = teamid
        self.flag = flag
        # self.value = value

    def __repr__(self):
        return '<solves %r>' % self.chal


class WrongKeys(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chalid = db.Column(db.Integer, db.ForeignKey('challenges.id'))
    teamid = db.Column(db.Integer, db.ForeignKey('teams.id'))
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    flag = db.Column(db.Text)
    chal = db.relationship('Challenges', foreign_keys="WrongKeys.chalid", lazy='joined')

    def __init__(self, teamid, chalid, flag):
        self.teamid = teamid
        self.chalid = chalid
        self.flag = flag

    def __repr__(self):
        return '<wrong %r>' % self.flag


class Tracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.BigInteger)
    team = db.Column(db.Integer, db.ForeignKey('teams.id'))
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, ip, team):
        self.ip = ip2long(ip)
        self.team = team

    def __repr__(self):
        return '<ip %r>' % self.team


class Announcements(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    description = db.Column(db.Text)
    chalid = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=True)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    chal = db.relationship('Challenges', foreign_keys='Announcements.chalid', lazy='joined')

    def __init__(self, title, description, challenge=None):
        self.title = title
        self.description = description
        if challenge:
            self.chalid = challenge.id
        else:
            self.chalid = None

    def __repr__(self):
        return '<announcement %s>' % self.title


class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Text)
    value = db.Column(db.Text)

    def __init__(self, key, value):
        self.key = key
        self.value = value

import os
import re

from flask import current_app as app, render_template, request, redirect, abort, jsonify, url_for, session, Blueprint, Response, send_file
from jinja2.exceptions import TemplateNotFound
from passlib.hash import bcrypt_sha256

from CTFd.utils import authed, is_setup, validate_url, get_config, set_config, sha512, cache, ctftime, view_after_ctf, ctf_started, \
    is_admin, unix_time
from CTFd.models import db, Challenges, Teams, Solves, Awards, Files, Pages, Announcements, get_solves_and_value
from CTFd import countries

views = Blueprint('views', __name__)


@views.before_request
def redirect_setup():
    if request.path.startswith("/static"):
        return
    if not is_setup() and request.path != "/setup":
        return redirect(url_for('views.setup'))


@views.route('/setup', methods=['GET', 'POST'])
def setup():
    # with app.app_context():
        # admin = Teams.query.filter_by(admin=True).first()

    if not is_setup():
        if not session.get('nonce'):
            session['nonce'] = sha512(os.urandom(10))
        if request.method == 'POST':
            ctf_name = request.form['ctf_name']
            ctf_name = set_config('ctf_name', ctf_name)

            flag_format = request.form['flag_format']
            flag_format = set_config('flag_format', flag_format)

            # CSS
            css = set_config('start', '')

            # Admin user
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            admin = Teams(name, email, password)
            admin.admin = True
            admin.banned = True

            # Index page
            page = Pages('index', """
    <img class="logo" src="{0}/static/original/img/logo.png" />

    <h3 class="text-center">
        Welcome to the THC CTF 2017 !
    </h3>

    <br/>

    <h6 class="text-center">
        <a href="https://github.com/ToulouseHackingConvention/CTFd/">scoreboard</a> based on <a href="https://github.com/isislab/CTFd">CTFd</a> and modified by <a href="https://github.com/arthaud">maxima</a>, <a href="https://github.com/palkeo">palkeo</a> and <a href="https://github.com/zadlg">zadig</a>.
    </h6>""".format(request.script_root))

            # max attempts per challenge
            max_tries = set_config("max_tries", 0)

            # Start time
            start = set_config('start', None)
            end = set_config('end', None)

            # Challenges cannot be viewed by unregistered users
            view_challenges_unregistered = set_config('view_challenges_unregistered', None)

            # Allow/Disallow registration
            prevent_registration = set_config('prevent_registration', None)

            # Verify emails
            verify_emails = set_config('verify_emails', None)

            mail_server = set_config('mail_server', None)
            mail_port = set_config('mail_port', None)
            mail_tls = set_config('mail_tls', None)
            mail_ssl = set_config('mail_ssl', None)
            mail_username = set_config('mail_username', None)
            mail_password = set_config('mail_password', None)

            setup = set_config('setup', True)

            db.session.add(page)
            db.session.add(admin)
            db.session.commit()
            db.session.close()
            app.setup = False
            with app.app_context():
                cache.clear()
            return redirect(url_for('views.index'))
        return render_template('setup.html', nonce=session.get('nonce'))
    return redirect(url_for('views.index'))


# Custom CSS handler
@views.route('/static/user.css')
def custom_css():
    return Response(get_config("css"), mimetype='text/css')


@views.route('/')
def index():
    announcements = Announcements.query.join(Challenges, Announcements.chalid == Challenges.id, isouter=True).order_by(Announcements.date.desc()).all()

    page = Pages.query.filter_by(route='index').first()
    content = page.html if page else ''

    return render_template('index.html', announcements=announcements, content=content)


@views.route('/announcement/last')
def last_announcement():
    announcement = Announcements.query.join(Challenges, Announcements.chalid == Challenges.id, isouter=True).order_by(Announcements.date.desc()).first()

    if not announcement:
        return jsonify(False)
    elif announcement.chalid:
        return jsonify({
            'type': 'hint',
            'title': announcement.title,
            'description': announcement.description,
            'date': unix_time(announcement.date),
            'chal_id': announcement.chal.id,
            'chal_name': announcement.chal.name,
        })
    else:
        return jsonify({
            'type': 'announcement',
            'title': announcement.title,
            'description': announcement.description,
            'date': unix_time(announcement.date),
        })


# Static HTML files
@views.route("/<template>")
def static_html(template):
    try:
        return render_template('%s.html' % template)
    except TemplateNotFound:
        page = Pages.query.filter_by(route=template).first_or_404()
        return render_template('page.html', content=page.html)


@views.route('/teams', defaults={'page': '1'})
@views.route('/teams/<int:page>')
def teams(page):
    page = abs(int(page))
    results_per_page = 50
    page_start = results_per_page * (page - 1)
    page_end = results_per_page * (page - 1) + results_per_page

    if get_config('verify_emails'):
        count = Teams.query.filter_by(verified=True, banned=False).count()
        teams = Teams.query.filter_by(verified=True, banned=False).slice(page_start, page_end).all()
    else:
        count = Teams.query.filter_by(banned=False).count()
        teams = Teams.query.filter_by(banned=False).slice(page_start, page_end).all()
    pages = int(count / results_per_page) + (count % results_per_page > 0)
    return render_template('teams.html', teams=teams, team_pages=pages, curr_page=page)


@views.route('/team/<int:teamid>', methods=['GET', 'POST'])
def team(teamid):
    if get_config('view_scoreboard_if_authed') and not authed():
        return redirect(url_for('auth.login', next=request.path))
    teamid = int(teamid)

    team = Teams.query.filter_by(id=teamid).first_or_404()
    score = team.score()
    place = team.place()

    solves_with_value = [
        (solve, value) for solve, value in get_solves_and_value()
        if solve.teamid == teamid]
    solves_with_value.sort(key=lambda solve_value: solve_value[0].date)

    if request.method == 'GET':
        return render_template('team.html', solves=solves_with_value, team=team, score=score, place=place)
    elif request.method == 'POST':
        json = {'solves': []}
        solves = Solves.query.filter_by(teamid=teamid)
        for x in solves:
            json['solves'].append({'id': x.id, 'chal': x.chalid, 'team': x.teamid})
        return jsonify(json)


@views.route('/profile', methods=['POST', 'GET'])
def profile():
    if authed():
        team = Teams.query.filter_by(id=session['id']).first()

        if request.method == "POST":
            errors = []

            name = request.form.get('name')
            email = request.form.get('email')
            website = request.form.get('website', '')
            affiliation = request.form.get('affiliation', '')
            country = request.form.get('country')

            if not get_config('prevent_name_change'):
                if not name:
                    errors.append('Pick a longer team name')
                else:
                    names = Teams.query.filter_by(name=name).first()
                    if names and name != team.name:
                        errors.append('That team name is already taken')

            if not email:
                errors.append('Pick a longer email')
            elif not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email):
                errors.append("That email doesn't look right")
            else:
                emails = Teams.query.filter_by(email=email).first()
                if emails and emails.id != team.id:
                    errors.append('That email has already been used')

            if request.form.get('new-password'):
                if request.form.get('new-password') != request.form.get('new-password-confirm'):
                    errors.append("These passwords don't match")
                elif not bcrypt_sha256.verify(request.form.get('current-password'), team.password):
                    errors.append("Your old password doesn't match what we have")

            if website and not validate_url(website):
                errors.append("That doesn't look like a valid URL")

            if country not in countries.keys:
                errors.append('Invalid country')

            if len(errors) > 0:
                return render_template('profile.html', name=name, email=email, website=website,
                                       affiliation=affiliation, country=country, countries=countries, errors=errors)
            else:
                if not get_config('prevent_name_change') and team.name != name:
                    team.name = name
                    session['username'] = name

                if team.email != email.lower():
                    team.email = email.lower()

                    if get_config('verify_emails'):
                        team.verified = False

                if request.form.get('new-password'):
                    team.password = bcrypt_sha256.encrypt(request.form['new-password'])

                team.website = website
                team.affiliation = affiliation
                team.country = country
                db.session.commit()
                db.session.close()
                return redirect(url_for('views.profile'))
        else:
            name = team.name
            email = team.email
            website = team.website
            affiliation = team.affiliation
            country = team.country
            prevent_name_change = get_config('prevent_name_change')
            confirm_email = get_config('verify_emails') and not team.verified
            return render_template('profile.html', name=name, email=email, website=website, affiliation=affiliation,
                                   country=country, countries=countries, prevent_name_change=prevent_name_change, confirm_email=confirm_email)
    else:
        return redirect(url_for('auth.login'))


@views.route('/files', defaults={'path': ''})
@views.route('/files/<path:path>')
def file_handler(path):
    f = Files.query.filter_by(location=path).first_or_404()
    if f.chal:
        if not is_admin():
            if not ctftime():
                if view_after_ctf() and ctf_started():
                    pass
                else:
                    abort(403)
    return send_file(os.path.join(app.root_path, 'uploads', f.location))

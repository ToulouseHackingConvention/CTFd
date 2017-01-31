import json
import logging
import operator
import re
import six
import time

from flask import render_template, request, redirect, jsonify, url_for, session, Blueprint
from sqlalchemy.sql import or_

from CTFd.utils import ctftime, view_after_ctf, authed, unix_time, get_kpm, user_can_view_challenges, is_admin, get_config, get_ip, is_verified, ctf_started, ctf_ended, ctf_name
from CTFd.models import db, Challenges, Files, Solves, WrongKeys, Tags, Teams, Awards, Announcements, get_solves_and_value

challenges = Blueprint('challenges', __name__)


@challenges.route('/challenges', methods=['GET'])
def challenges_view():
    errors = []
    start = get_config('start') or 0
    end = get_config('end') or 0
    if not is_admin(): # User is not an admin
        if not ctftime():
            # It is not CTF time
            if view_after_ctf(): # But we are allowed to view after the CTF ends
                pass
            else:  # We are NOT allowed to view after the CTF ends
                if get_config('start') and not ctf_started():
                    errors.append('{} has not started yet'.format(ctf_name()))
                if (get_config('end') and ctf_ended()) and not view_after_ctf():
                    errors.append('{} has ended'.format(ctf_name()))
                return render_template('chals.html', errors=errors, start=int(start), end=int(end))
        if get_config('verify_emails') and not is_verified(): # User is not confirmed
            return redirect(url_for('auth.confirm_user'))
    if user_can_view_challenges(): # Do we allow unauthenticated users?
        if get_config('start') and not ctf_started():
            errors.append('{} has not started yet'.format(ctf_name()))
        if (get_config('end') and ctf_ended()) and not view_after_ctf():
            errors.append('{} has ended'.format(ctf_name()))
        return render_template('chals.html', errors=errors, start=int(start), end=int(end))
    else:
        return redirect(url_for('auth.login', next='challenges'))


@challenges.route('/chals', methods=['GET'])
def chals():
    if not is_admin():
        if not ctftime():
            if view_after_ctf():
                pass
            else:
                return redirect(url_for('views.index'))
    if user_can_view_challenges() and (ctf_started() or is_admin()):
        chals = Challenges.query.filter(or_(Challenges.hidden != True, Challenges.hidden == None)).order_by(Challenges.value).all()

        json = {'game': []}
        for chal in chals:
            tags = [tag.tag for tag in Tags.query.add_columns('tag').filter_by(chal=chal.id).all()]
            files = [str(f.location) for f in Files.query.filter_by(chal=chal.id).all()]
            hints = [{'title': hint.title, 'description': hint.description}
                     for hint in Announcements.query.filter_by(chalid=chal.id).order_by(Announcements.date.asc()).all()]
            json['game'].append({
                'id': chal.id,
                'name': chal.name,
                'value': chal.value,
                'description': chal.description,
                'category': chal.category,
                'down': chal.down,
                'files': files,
                'tags': tags,
                'hints': hints,
            })

        db.session.close()
        return jsonify(json)
    else:
        db.session.close()
        return redirect(url_for('auth.login', next='chals'))


@challenges.route('/chals/solves')
def solves_per_chal():
    if not user_can_view_challenges():
        return redirect(url_for('auth.login', next=request.path))
    solves_sub = db.session.query(Solves.chalid, db.func.count(Solves.chalid).label('solves')).join(Teams, Solves.teamid == Teams.id).filter(Teams.banned == False).group_by(Solves.chalid).subquery()
    solves = db.session.query(solves_sub.columns.chalid, solves_sub.columns.solves, Challenges.name) \
                       .join(Challenges, solves_sub.columns.chalid == Challenges.id).all()
    json = {}
    for chal, count, name in solves:
        json[chal] = count
    db.session.close()
    return jsonify(json)


@challenges.route('/solves')
@challenges.route('/solves/<int:teamid>')
def solves(teamid=None):
    if teamid is None:
        if is_admin() or user_can_view_challenges():
            teamid = session['id']
        else:
            return redirect(url_for('auth.login', next='solves'))
    teamid = int(teamid)

    user_solves = []
    for solve, value in get_solves_and_value(is_admin=is_admin()):
        if solve.teamid == teamid:
            j = {
                'team': solve.teamid,
                'value': value,
                'time': unix_time(solve.date),
            }
            if isinstance(solve, Solves):
                j['chalid'] = solve.chalid
                j['chal'] = solve.chal.name
                j['category'] = solve.chal.category
            elif isinstance(solve, Awards):
                j['chalid'] = None
                j['chal'] = solve.name
                j['category'] = solve.category
            else:
                raise RuntimeError(
                    "Objects returned by get_solves_and_value "
                    "should be Solves or Awards")
            user_solves.append(j)

    user_solves = sorted(user_solves, key=operator.itemgetter('time'))
    return jsonify({'solves': user_solves})


@challenges.route('/maxattempts')
def attempts():
    if not user_can_view_challenges():
        return redirect(url_for('auth.login', next=request.path))
    chals = Challenges.query.add_columns('id').all()
    json = {'maxattempts': []}
    for chal, chalid in chals:
        fails = WrongKeys.query.filter_by(teamid=session['id'], chalid=chalid).count()
        if fails >= int(get_config("max_tries")) and int(get_config("max_tries")) > 0:
            json['maxattempts'].append({'chalid': chalid})
    return jsonify(json)


@challenges.route('/fails/<int:teamid>', methods=['GET'])
def fails(teamid):
    fails = WrongKeys.query.filter_by(teamid=teamid).count()
    solves = Solves.query.filter_by(teamid=teamid).count()
    db.session.close()
    json = {'fails': str(fails), 'solves': str(solves)}
    return jsonify(json)


@challenges.route('/chal/<int:chalid>/solves', methods=['GET'])
def who_solved(chalid):
    if not user_can_view_challenges():
        return redirect(url_for('auth.login', next=request.path))
    solves = Solves.query.join(Teams).filter(Solves.chalid == chalid, Teams.banned == False).order_by(Solves.date)
    json = {'teams': []}
    for solve in solves:
        json['teams'].append({'id': solve.team.id, 'name': solve.team.name, 'date': solve.date})
    return jsonify(json)


def normalize_key(key):
    key = six.text_type(key.strip().lower())
    flag_format = get_config('flag_format')

    if flag_format:
        match = re.match('^%s$' % flag_format.strip('^$'), key, re.IGNORECASE)
        if match:
            try:
                key = match.group('flag')
            except IndexError:
                pass # the flag format does not contain (?P<flag>...)

    return key


@challenges.route('/chal/<int:chalid>', methods=['POST'])
def chal(chalid):
    if ctf_ended() and not view_after_ctf():
        return redirect(url_for('challenges.challenges_view'))
    if not user_can_view_challenges():
        return redirect(url_for('auth.login', next=request.path))
    if authed() and is_verified() and (ctf_started() or view_after_ctf()):
        fails = WrongKeys.query.filter_by(teamid=session['id'], chalid=chalid).count()
        logger = logging.getLogger('keys')
        data = (time.strftime("%m/%d/%Y %X"), session['username'].encode('utf-8'), request.form['key'].encode('utf-8'), get_kpm(session['id']))
        print("[{0}] {1} submitted {2} with kpm {3}".format(*data))

        # Anti-bruteforce / submitting keys too quickly
        if get_kpm(session['id']) > 10:
            if ctftime():
                wrong = WrongKeys(session['id'], chalid, request.form['key'])
                db.session.add(wrong)
                db.session.commit()
                db.session.close()
            logger.warn("[{0}] {1} submitted {2} with kpm {3} [TOO FAST]".format(*data))
            # return '3' # Submitting too fast
            return jsonify({'status': '3', 'message': "You're submitting keys too fast. Slow down."})

        solves = Solves.query.filter_by(teamid=session['id'], chalid=chalid).first()

        # Challenge not solved yet
        if not solves:
            chal = Challenges.query.filter_by(id=chalid).first_or_404()

            if chal.hidden:
                return jsonify({'status': '0', 'message': 'You are not supposed to see this'})

            if chal.down:
                return jsonify({'status': '0', 'message': 'Challenge currently down'})

            key = normalize_key(request.form['key'])
            keys = json.loads(chal.flags)

            # Hit max attempts
            max_tries = int(get_config("max_tries"))
            if fails >= max_tries > 0:
                return jsonify({
                    'status': '0',
                    'message': "You have 0 tries remaining"
                })

            for x in keys:
                if x['type'] == 0: # static key
                    if x['flag'] and normalize_key(x['flag']) == key:
                        if ctftime():
                            solve = Solves(chalid=chalid, teamid=session['id'], ip=get_ip(), flag=key)
                            db.session.add(solve)
                            db.session.commit()
                            db.session.close()
                        logger.info("[{0}] {1} submitted {2} with kpm {3} [CORRECT]".format(*data))
                        # return '1' # key was correct
                        return jsonify({'status': '1', 'message': 'Correct'})
                elif x['type'] == 1: # regex
                    if x['flag'] and re.match('^%s$' % x['flag'].strip('^$'), key, re.IGNORECASE):
                        if ctftime():
                            solve = Solves(chalid=chalid, teamid=session['id'], ip=get_ip(), flag=key)
                            db.session.add(solve)
                            db.session.commit()
                            db.session.close()
                        logger.info("[{0}] {1} submitted {2} with kpm {3} [CORRECT]".format(*data))
                        # return '1' # key was correct
                        return jsonify({'status': '1', 'message': 'Correct'})

            if ctftime():
                wrong = WrongKeys(session['id'], chalid, request.form['key'])
                db.session.add(wrong)
                db.session.commit()
                db.session.close()
            logger.info("[{0}] {1} submitted {2} with kpm {3} [WRONG]".format(*data))
            # return '0' # key was wrong
            if max_tries:
                attempts_left = max_tries - fails
                tries_str = 'tries'
                if attempts_left == 1:
                    tries_str = 'try'
                return jsonify({'status': '0', 'message': 'Incorrect. You have {} {} remaining.'.format(attempts_left, tries_str)})
            else:
                return jsonify({'status': '0', 'message': 'Incorrect'})

        # Challenge already solved
        else:
            logger.info("{0} submitted {1} with kpm {2} [ALREADY SOLVED]".format(*data))
            # return '2' # challenge was already solved
            return jsonify({'status': '2', 'message': 'You already solved this'})
    else:
        return '-1'

import collections
import operator

from flask import render_template, jsonify, Blueprint, redirect, url_for, request
from sqlalchemy.sql.expression import union_all

from CTFd.utils import unix_time, authed, get_config
from CTFd.models import db, Teams, Solves, Awards, Challenges, get_solves_and_value, score_by_team

scoreboard = Blueprint('scoreboard', __name__)


@scoreboard.route('/scoreboard')
def scoreboard_view():
    # TODO: This should be a decorator!
    if get_config('view_scoreboard_if_authed') and not authed():
        return redirect(url_for('auth.login', next=request.path))

    return render_template('scoreboard.html',
                           teams=score_by_team().most_common())


@scoreboard.route('/scores')
def scores():
    if get_config('view_scoreboard_if_authed') and not authed():
        return redirect(url_for('auth.login', next=request.path))

    standings = [
        {'pos': i + 1,
         'id': team.id,
         'team': team.name,
         'score': score}
        for i, (team, score) in enumerate(score_by_team())
    ]
    return jsonify({'standings': standings})


@scoreboard.route('/top/<int:count>')
def topteams(count):
    if get_config('view_scoreboard_if_authed') and not authed():
        return redirect(url_for('auth.login', next=request.path))

    try:
        count = int(count)
    except ValueError:
        count = 10
    if count > 20 or count < 0:
        count = 10

    team_ids = set(
        team.id for team, score in score_by_team().most_common(count))

    scores = collections.defaultdict(list)
    for solve, value in get_solves_and_value():
        if solve.teamid in team_ids:
            scores[solve.team.name].append({
                # It can be an award, without chalid
                'chal': solve.chalid if isinstance(solve, Solves) else None,
                'team': solve.teamid,
                'value': value,
                'time': unix_time(solve.date),
            })

    # Re-sort by time
    scores = {
        team_name: sorted(solves, key=operator.itemgetter('time'))
        for team_name, solves in scores.items()
    }

    return jsonify({'scores': scores})

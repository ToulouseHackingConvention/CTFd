function updatescores () {
  $.get(script_root + '/scores', function(data) {
    teams = $.parseJSON(JSON.stringify(data));
    $('#scoreboard > tbody').empty()
    for (var i = 0; i < teams['standings'].length; i++) {
      var team = teams['standings'][i];
      row = '<tr>';
      row += '<td>' + (i+1) + '</td>';
      row += '<td><a href="' + script_root + '/team/' + team.id + '">' + htmlentities(team.name) + '</a></td>';
      if (team.country.length > 0) {
        row += '<td><img src="' + script_root + '/static/original/img/flags/' + team.country + '.png"></td>';
      } else {
        row += '<td></td>';
      }
      row += '<td>' + team.score + '</td>';
      row += '</tr>';
      $('#scoreboard > tbody').append(row)
    };
  });
}

function cumulativesum (arr) {
    var result = arr.concat();
    for (var i = 0; i < arr.length; i++){
        result[i] = arr.slice(0, i + 1).reduce(function(p, i){ return p + i; });
    }
    return result
}

function UTCtoDate(utc){
    var d = new Date(0)
    d.setUTCSeconds(utc)
    return d;
}

function scoregraph () {
    $.get(script_root + '/top/10', function( data ) {
        var scores = $.parseJSON(JSON.stringify(data));
        scores = scores['scores'];
        if (Object.keys(scores).length == 0 ){
            return;
        }

        var teams = Object.keys(scores);
        var traces = [];
        for(var i = 0; i < teams.length; i++){
            var team_score = [];
            var times = [];
            for(var j = 0; j < scores[teams[i]].length; j++){
                team_score.push(scores[teams[i]][j].value);
                var date = moment(scores[teams[i]][j].time * 1000);
                times.push(date.toDate());
            }
            team_score = cumulativesum(team_score);
            var trace = {
                x: times,
                y: team_score,
                mode: 'lines+markers',
                name: teams[i]
            }
            traces.push(trace);
        }

        var layout = {
            title: 'Top 10 Teams'
        };
        console.log(traces);

        Plotly.newPlot('score-graph', traces, layout);


        $('#score-graph').show()
    });
}

function update(){
  updatescores();
  scoregraph();
}

setInterval(update, 60 * 1000); // update scores every minute
scoregraph();

window.onresize = function () {
    Plotly.Plots.resize(document.getElementById('score-graph'));
};

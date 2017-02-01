var last_announcement;

function poll_announcements() {
    $.get(script_root + "/announcement/last", function (announcement) {
      if (announcement && announcement.date > last_announcement) {
        var modal = $('#alert-announcement');
        var title = 'Announcement: ' + announcement.title;

        if (announcement.type == 'hint') {
          title = 'New Hint: ' + announcement.chal_name;
          if (announcement.title.length > 0) {
            title += ': ' + announcement.title;
          }
        }

        modal.find('.modal-header h3').text(title);
        modal.find('.modal-body').html(marked(announcement.description, {'gfm': true, 'breaks': true}));
        modal.modal();

        last_announcement = announcement.date;
      }
    });
}

function init_announcements() {
    // get timestamp of last announcement
    $.get(script_root + "/announcement/last", function (announcement) {
      if (announcement) {
        last_announcement = announcement.date;
      } else {
        last_announcement = 0;
      }
    });
}

$(function() {
    init_announcements();
});

setInterval(poll_announcements, 60 * 1000); // check for new announcement every minute

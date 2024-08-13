document.addEventListener("DOMContentLoaded", function () {
  var calendarEl = document.getElementById("calendar");
  var calendar = new FullCalendar.Calendar(calendarEl, {
    themeSystem: "bootstrap5",
    height: 650,
    headerToolbar: {
      end: "today",
    },
    footerToolbar: {
      center: "prevYear,prev,next,nextYear",
    },
    buttonText: {
      today: "Сегодня",
    },
    initialView: "dayGridMonth",
    fixedWeekCount: false,
    navLinks: true,
    navLinkDayClick: function (date) {
      var localDate = new Date(
        date.getTime() - date.getTimezoneOffset() * 60000
      );
      var formattedDate = localDate.toISOString().split("T")[0];
      var url = "/daystats/" + formattedDate + "/";
      window.location.href = url;
    },
    firstDay: 1,
    locale: "ru",
    events: "/calendar_api/",
  });
  calendar.render();
});

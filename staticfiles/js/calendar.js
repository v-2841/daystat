document.addEventListener("DOMContentLoaded", function () {
    var calendarEl = document.getElementById("calendar");
    var calendar = new FullCalendar.Calendar(calendarEl, {
        themeSystem: "bootstrap5",
        height: "auto",
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

    var hammer = new Hammer(calendarEl);
    hammer.get("swipe").set({
        direction: Hammer.DIRECTION_HORIZONTAL,
        threshold: 20,
        velocity: 0.2,
    });
    hammer.on("swipeleft", function () {
        calendar.next();
    });
    hammer.on("swiperight", function () {
        calendar.prev();
    });

    if (window.matchMedia("(pointer: coarse)").matches) {
        function clearCalendarButtonFocus() {
            var activeElement = document.activeElement;
            if (activeElement && activeElement.closest("#calendar")) {
                if (activeElement.classList.contains("fc-button")) {
                    activeElement.blur();
                }
            }
        }

        calendarEl.addEventListener(
            "pointerup",
            function () {
                window.setTimeout(clearCalendarButtonFocus, 0);
            },
            true
        );
        calendarEl.addEventListener(
            "touchend",
            function () {
                window.setTimeout(clearCalendarButtonFocus, 0);
            },
            true
        );
    }
});

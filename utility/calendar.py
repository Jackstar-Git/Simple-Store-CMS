weekday_map = {
    1: "Montag",
    2: "Dienstag",
    3: "Mittwoch",
    4: "Donnerstag",
    5: "Freitag",
    6: "Samstag",
    7: "Sonntag"
}

month_map = {
    1: "Januar",
    2: "Februar",
    3: "März",
    4: "April",
    5: "Mai",
    6: "Juni",
    7: "Juli",
    8: "August",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Dezember"
}

def day_of_week(year, month, day, week_start = 0):
    week_shift: dict =  {
        0: 5,
        1: 4,
        2: 3,
        3: 2,
        4: 1,
        5: 0,
        6: 6
    }

    if month < 3:
        month += 12
        year -= 1
    k = year % 100
    j = year // 100
    zeller_day = (day + (13 * (month + 1)) // 5 + k + (k // 4) + (j // 4) - (2 * j)) % 7
    return (zeller_day + week_shift[week_start]) % 7

def is_leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def days_in_month(year, month):
    if month in [4, 6, 9, 11]:
        return 30
    elif month == 2:
        return 29 if is_leap_year(year) else 28
    return 31

def generate_calendar(year, month, week_start = 0):
    days = days_in_month(year, month)
    first_day_weekday = day_of_week(year, month, 1, week_start)

    calendar = []
    week = ["" for _ in range(first_day_weekday)]
    for day in range(1, days + 1):
        week.append(day)
        if len(week) == 7:
            calendar.append(week)
            week = []
    if week:
        while len(week) < 7:
            week.append("")
        calendar.append(week)
    return calendar
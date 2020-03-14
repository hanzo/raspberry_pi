from collections import defaultdict
import csv
from datetime import datetime
import dateutil.parser
import json
import pytz


PACIFIC_TZ = pytz.timezone("US/Pacific")

# Convert the given UTC datetime to Pacific Time (PST or PDT depending on DST)
def convert_utc_to_pt(utc_dt):
    pst_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(PACIFIC_TZ)
    return PACIFIC_TZ.normalize(pst_dt)


def load_indoor_temps(filename):
    indoor_temps = []
    with open(filename) as indoor_file:
        temp_reader = csv.reader(indoor_file)
        for row in temp_reader:
            if row:
                # round temperature to 2 decimal places
                temp = round(float(row[1]), 2)

                # timestamps are UTC. append the string 'UTC' so that the resulting datetime will be TZ aware
                utc_dt = dateutil.parser.parse(f"{row[0]} UTC")
                pt_dt = convert_utc_to_pt(utc_dt)

                # print(f"{row[0]}, {utc_dt.hour}, {utc_dt.tzinfo} > {pt_dt}, {pt_dt.tzinfo}")
                indoor_temps.append([pt_dt, temp])
    return indoor_temps


def load_outdoor_temps(filename):
    outdoor_temps = []
    with open(filename) as outdoor_file:
        temp_reader = csv.reader(outdoor_file)
        for row in temp_reader:
            if row:
                # round temperature to 2 decimal places
                temp = round(float(row[2]), 2)

                # timestamps are UTC. append the string 'UTC' so that the resulting datetime will be TZ aware
                utc_dt = dateutil.parser.parse(f"{row[1]} UTC")
                pt_dt = convert_utc_to_pt(utc_dt)

                outdoor_temps.append([pt_dt, temp])
    return outdoor_temps


def get_temps_per_hour(temp_list):
    temps_per_hour = defaultdict(list)

    for temp_pair in temp_list:
        dt = temp_pair[0]
        temp = temp_pair[1]

        # dict key is combination of date and hour, e.g. "2020-03-01 09"
        hour_str = f"{dt.date()} "
        if dt.hour < 10:
            hour_str += "0"
        hour_str += str(dt.hour)
        # print(hour_str)

        temps_per_hour[hour_str].append(temp)

    return temps_per_hour


def main():
    outdoor_temps = load_outdoor_temps("outdoor_temp_readings/sample.csv")
    indoor_temps = load_indoor_temps("indoor_temp_readings/sample.csv")

    # print(indoor_temps)
    # print(outdoor_temps)

    indoor_temps_per_hour = get_temps_per_hour(indoor_temps)
    print(json.dumps(indoor_temps_per_hour, indent=2))

    outdoor_temps_per_hour = get_temps_per_hour(outdoor_temps)
    print(json.dumps(outdoor_temps_per_hour, indent=2))


if __name__ == "__main__":
    main()

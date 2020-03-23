from collections import defaultdict
import csv
from dataclasses import dataclass, field
from datetime import datetime
import dateutil.parser
from json import dumps
import pytz
import statistics


# Class to record temperature statistics for a particular hour
@dataclass
class HourStats:
    indoor_temps: list = field(default_factory=list)
    outdoor_temps: list = field(default_factory=list)
    avg_indoor_temp: float = 0
    max_indoor_temp: float = 0
    avg_outdoor_temp: float = 0
    is_habitable_hour: bool = False


# Class to record temperature statistics for a particular date
@dataclass
class DateStats:
    hours: defaultdict = field(default_factory=lambda: defaultdict(HourStats))
    avg_indoor_temp: float = 0
    max_indoor_temp: int = 0
    avg_outdoor_temp: float = 0
    adequate_hour_count: int = 0
    inadequate_hour_count: int = 0
    majority_adequate: bool = True


PACIFIC_TZ = pytz.timezone("US/Pacific")

# "Heat capable of maintaining a room temperature of 68°F shall be made available to each occupied
# habitable room for 13 hours each day between 5:00 a.m. and 11:00 a.m. and 3:00 p.m. to 10:00 p.m"
# https://sfdbi.org/ftp/uploadedfiles/dbi/Key_Information/19HeatOrdinance0506.pdf
HABITABLE_TEMP = 68
HABITABLE_HEAT_HOURS = frozenset([5, 6, 7, 8, 9, 10, 11, 15, 16, 17, 18, 19, 20])

# Average difference between indoor and outdoor temperature. Calculated as 7.34 in google sheets.
# TODO: calculate this number within this script
INDOOR_OUTDOOR_DELTA = 10

# Return true if the given hour is within the hours for which the SF Heat Ordinance requires
# a minimum temperature of 68°F must be achievable
def is_heat_required(hour: int) -> bool:
    return hour in HABITABLE_HEAT_HOURS


# Return true if the given temperature meets the minimum habitable temperature
# required by the SF Heat Ordinance
def is_habitable_temp(temp: int) -> bool:
    return temp >= HABITABLE_TEMP


# Convert the given UTC datetime to Pacific Time (PST or PDT depending on DST)
def convert_utc_to_pt(utc_dt: datetime) -> datetime:
    pst_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(PACIFIC_TZ)
    return PACIFIC_TZ.normalize(pst_dt)


# Load indoor temperatures from file, sanitize the data and add it to the dict
def load_indoor_temps(daily_dict: defaultdict(DateStats), filename: str) -> None:
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

                # pad zeros for sort order, e.g. 2 -> 02
                hour_str = f"{pt_dt.hour:02}"
                daily_dict[pt_dt.date()].hours[hour_str].indoor_temps.append(temp)


# Load outdoor temperatures from file, sanitize the data and add it to the dict
def load_outdoor_temps(daily_dict: defaultdict(DateStats), filename: str) -> None:
    with open(filename) as outdoor_file:
        temp_reader = csv.reader(outdoor_file)
        for row in temp_reader:
            if row:
                # round temperature to 2 decimal places
                temp = round(float(row[2]), 2)

                # timestamps are UTC. append the string 'UTC' so that the resulting datetime will be TZ aware
                utc_dt = dateutil.parser.parse(f"{row[1]} UTC")
                pt_dt = convert_utc_to_pt(utc_dt)

                # pad zeros for sort order, e.g. 2 -> 02
                hour_str = f"{pt_dt.hour:02}"
                daily_dict[pt_dt.date()].hours[hour_str].outdoor_temps.append(temp)


def calculate_temp_data(extrapolate_data=True):
    temps_per_day = defaultdict(DateStats)

    total_adequate_hours = 0
    total_inadequate_hours = 0

    # load_indoor_temps(temps_per_day, "indoor_temp_readings/sample.csv")
    # load_outdoor_temps(temps_per_day, "outdoor_temp_readings/sample.csv")
    # load_indoor_temps(temps_per_day, "indoor_temp_readings/2020-01-12_2020-02-13.csv")
    # load_outdoor_temps(temps_per_day, "outdoor_temp_readings/2020-01-12_2020-02-13.csv")
    load_indoor_temps(temps_per_day, "indoor_temp_readings/2020-01-12_2020-03-10.csv")
    load_outdoor_temps(temps_per_day, "outdoor_temp_readings/2019-03-10_2020-03-10.csv")

    for date, date_stats in sorted(temps_per_day.items()):
        daily_max_indoor_temp = 0
        for hour, hour_stats in sorted(date_stats.hours.items()):
            # calculate average hourly temperatures
            if hour_stats.outdoor_temps:
                hour_stats.avg_outdoor_temp = round(
                    statistics.mean(hour_stats.outdoor_temps), 2
                )
                if hour_stats.indoor_temps:
                    hour_stats.avg_indoor_temp = round(
                        statistics.mean(hour_stats.indoor_temps), 2
                    )
                    hour_stats.max_indoor_temp = round(max(hour_stats.indoor_temps), 2)
                    daily_max_indoor_temp = max(
                        daily_max_indoor_temp, hour_stats.max_indoor_temp
                    )
                elif extrapolate_data:
                    # If we have outdoor data but no indoor data, estimate the avg indoor temperature
                    hour_stats.avg_indoor_temp = (
                        hour_stats.avg_outdoor_temp + INDOOR_OUTDOOR_DELTA
                    )
                    daily_max_indoor_temp = max(
                        daily_max_indoor_temp, hour_stats.avg_indoor_temp
                    )
                else:
                    print(f"no indoor temperature data for {date} {hour}, skipping")
                    continue

            hour_stats.is_habitable_hour = is_heat_required(int(hour))
            if hour_stats.is_habitable_hour:
                if is_habitable_temp(hour_stats.avg_indoor_temp):
                    date_stats.adequate_hour_count += 1
                    total_adequate_hours += 1
                else:
                    date_stats.inadequate_hour_count += 1
                    total_inadequate_hours += 1

            # print(f"{date} {hour}: {hour_stats}")

        date_stats.max_indoor_temp = daily_max_indoor_temp
        date_stats.majority_adequate = (
            date_stats.adequate_hour_count >= date_stats.inadequate_hour_count
        )
        # print(f"{date}: {date_stats}")
        print(
            f"{date}: {date_stats.majority_adequate}, {date_stats.adequate_hour_count}, {date_stats.inadequate_hour_count}, {date_stats.max_indoor_temp}"
        )

    total_habitable_hours = total_adequate_hours + total_inadequate_hours
    print(
        f"assuming that the indoor temp was {INDOOR_OUTDOOR_DELTA} degrees warmer than outside, {total_inadequate_hours}/{total_habitable_hours} ({round(100*total_inadequate_hours/total_habitable_hours, 2)}%) of habitable hours were below {HABITABLE_TEMP} degrees"
    )


if __name__ == "__main__":
    calculate_temp_data()

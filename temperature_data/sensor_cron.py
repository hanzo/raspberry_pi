# Source: https://pimylifeup.com/raspberry-pi-temperature-sensor/
#
# Create cron job on pi to run this script every 10 minutes:
#    crontab -e
#    */10 * * * * python3 /[path_to_script]/sensor_cron.py


from datetime import datetime
import os
import glob
import time

os.system("modprobe w1-gpio")
os.system("modprobe w1-therm")

base_dir = "/sys/bus/w1/devices/"
device_folder = glob.glob(base_dir + "28*")[0]
device_file = device_folder + "/w1_slave"


def read_temp_raw():
    f = open(device_file, "r")
    lines = f.readlines()
    f.close()
    return lines


def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != "YES":
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find("t=")
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2 :]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        # return temp_c, temp_f
        return temp_f


with open("/home/hans/python_scripts/temperature_sensor/output.csv", "a") as outfile:
    outfile.write(f"{datetime.utcnow()},{read_temp()}\n")

#!/usr/bin/python3
"""
simple python3 script to send light detected by bh1750 sensor
python3 module required:
# apt install python3-smbus
# apt install python3-paho-mqtt

"""

import time
import sys
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import os
import smbus

""" ---- config -------- """

MQTT_HOST = ''
MQTT_PORT = 1883
MQTT_CLIENT_ID = os.popen('hostname').read().rstrip() + '-light'
LIGHT_INTERVAL = 300

""" ---------------------------------"""

DEVICE     = 0x23
POWER_DOWN = 0x00
POWER_ON   = 0x01
RESET      = 0x07
bus = smbus.SMBus(1)

auth = {
  'username':"MQTT_USER",
  'password':"MQTT_PASS"
}

def convertToNumber(data):
    result=(data[1] + (256 * data[0])) / 1.2
    return (result)

def readLight(addr=DEVICE):
    try:
        data = bus.read_i2c_block_data(addr,0x20)
        return format(convertToNumber(data),'.2f')
    except:
        return "unknown"

def percentage_change(current, previous):
    if previous != 0 and current != previous:
        return abs(float(current - previous) / abs(previous) * 100)
    elif previous == 0 and current != previous:
        return 100.0
    else:
        return 0.0

def detect_light(mqttclient,interval):
    """
    function to measure light every 1 sek and publish every X seconds.
    When light changes more than 10%, it will immidiately published
    loop every 100ms
    """
    lightLevel = float(readLight())
    mqttclient.publish("CHANNEL/Light/state",
                        payload=lightLevel,
                        qos=1,
                        retain=True)
    last_published = lightLevel

    while True:
        count = 0
        while count < interval:
            lightLevel = float(readLight())
            # if current light change is more than 10%, publish immidiately
            if percentage_change(lightLevel,last_published) > 10.0:
                mqttclient.publish("CHANNEL/Light/state",
                                    payload=lightLevel,
                                    qos=1,
                                    retain=True)
                last_published = lightLevel
            count += 1
            time.sleep(1)

        mqttclient.publish("CHANNEL/Light/state",
                            payload=lightLevel,
                            qos=1,
                            retain=True)
        last_published = lightLevel

def on_disconnect(client, userdata,rc=0):
    print("DisConnected result code "+str(rc))
    client.connected_flag = False
    client.disconnect_flag=True

def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag = True
        print("connected to MQTT Server")
    else:
        print("Bad connection Returned code=",rc)
        client.bad_connection_flag = True

def main():
    """
    Main function
    """
    mqtt.Client.connected_flag = False
    mqtt.Client.bad_connection_flag = False
    mqttclient = mqtt.Client(MQTT_CLIENT_ID)
    mqttclient.on_connect =  on_connect
    mqttclient.on_disconnect = on_disconnect
    mqttclient.loop_start()

    print("connecting to MQTT Server: " + MQTT_HOST + ":" + str(MQTT_PORT) + "...")
    try:
        mqttclient.connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)
    except:
        print("ERROR: can't connect to MQTT Server")
        exit(1)

    while not mqttclient.connected_flag and not mqttclient.bad_connection_flag:
        time.sleep(1)

    if mqttclient.bad_connection_flag:
        mqttclient.loop_stop()
        sys.exit()

    detect_light(mqttclient,LIGHT_INTERVAL)

if __name__=="__main__":
   main()

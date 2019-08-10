#!/usr/bin/env python3

from crcmod.predefined import Crc
import socketserver
import socket
from struct import pack, unpack, error
from datetime import datetime, timedelta
from osm_shortlink import short_osm
from binascii import hexlify

from models import initDB, Device, Position, connectDB, disconnectDB
from notify import notify_position


READ_TIMEOUT_SECS = 300


class GPSServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    def __init__(self, *args, **kwargs):
        self.allow_reuse_address = True
        self.serial_number = 1
        self.last_location = (0, 0)
        self.last_notified = datetime(2000, 1, 1)
        super().__init__(*args, **kwargs)


def calc_crc(data):
    crc16 = Crc('x25')
    crc16.update(data)
    return crc16.crcValue


class GP06(socketserver.StreamRequestHandler):

    def __init__(self, *args, **kwargs):
        self.imea = None
        super().__init__(*args, **kwargs)

    def send_response(self, proto, body):
        length = len(body) + 5
        start_code = 0x7878
        checksummable_data = pack(
            '!BB{}sH'.format(len(body)),
            length,
            proto,
            body,
            self.server.serial_number
        )
        error_check = calc_crc(checksummable_data)
        data = pack(
            '!h{}sHBB'.format(len(checksummable_data)),
            start_code,
            checksummable_data,
            error_check,
            0x0d, 0x0a
        )
        # print('Sending {}'.format(data))
        self.wfile.write(data)
        self.server.serial_number += 1

    def unknown_packet_type(self, t, data):
        print('Unknown packet type {}'.format(t))

    def login(self, t, data):
        imea, = unpack('8s', data)
        self.imea = hexlify(imea).decode('utf-8')
        print('IMEA: {}'.format(self.imea))

        self.send_response(0x01, b'')

    def location(self, t, data):
        (
            raw_date_time, quantity_sats, raw_latitude, raw_longitude,
            speed, course_status, mcc, mnc, lac, cell_id,
        ) = unpack('!6sBLLBHHBH3s', data)
        year, month, day, hour, minute, second = unpack('BBBBBB', raw_date_time)
        dt = datetime(2000+year, month, day, hour, minute, second)
        bit_len = quantity_sats >> 4 & 0x0f
        num_sats = quantity_sats & 0x0f
        latitude_degrees, latitude_minutes = divmod(raw_latitude/30000, 60)
        latitude = round(latitude_degrees + latitude_minutes/60, 6)
        longitude_degrees, longitude_minutes = divmod(raw_longitude/30000, 60)
        longitude = round(longitude_degrees + longitude_minutes/60, 6)
        differential = bool(course_status & 0x2000)
        gps_lock = bool(course_status & 0x1000)
        west = bool(course_status & 0x0800)
        signed_longitude = longitude * (-1 if west else 1)
        north = bool(course_status & 0x0400)
        signed_latitude = latitude * (1 if north else -1)
        EW = 'W' if west else 'E'
        NS = 'N' if north else 'N'
        course = course_status & 0x03ff
        cell_data = {
            'country_code': mcc,
            'network_code': mnc,
            'location_code': lac,
            'cell_id': cell_id
        }
        print("""
At {}
{} satellites
Position is {}{} {}{}
Speed: {}km/h
Course: {}deg
Lock: {} {}
Cell: {}
OSM: {}
Google: {}
            """.format(
                dt.isoformat(),
                num_sats,
                longitude, EW, latitude, NS,
                speed,
                course,
                gps_lock, 'Differential' if differential else 'Realtime',
                cell_data,
                short_osm(signed_latitude, signed_longitude) + '?m',
                'http://maps.google.com/maps?q={}{},{}{}'.format(
                    NS, latitude, EW, longitude
                )
            )
        )

        if self.imea is None:
            return

        device, created = Device.get_or_create(
            device_id=self.imea
        )
        device.log_position(
            Position(
                num_sats=num_sats,
                timestamp=dt,
                longitude=signed_longitude,
                latitude=signed_latitude,
                speed=speed,
                course=course
            )
        )

        print('dt is', dt, dt-self.server.last_notified)
        if dt - self.server.last_notified > timedelta(minutes=60):
            print('Time to notify')
            notify_position(signed_latitude, signed_longitude, self.imea)
            self.server.last_notified = dt


    def heartbeat(self, t, data):
        terminfo, voltage, gsm_strength, alarm, language_code = unpack('!BBBBB', data)
        gpo = bool(terminfo & 0x80)
        gps_status = bool(terminfo & 0x40)
        alarms_1 = {
            0x4: 'SOS',
            0x3: 'Low Batt',
            0x2: 'Power Cut',
            0x1: 'Shock',
        }.get(terminfo >> 3 & 0x7, 'None')
        charge = bool(terminfo & 0x04)
        gpi = bool(terminfo & 0x02)
        active = bool(terminfo & 0x01)
        alarms_2 = {
            0x1: 'SOS',
            0x2: 'Power Cut',
            0x3: 'Shock',
            0x4: 'Fence In',
            0x5: 'Fence Out',
        }.get(alarm, 'None')
        language = {
            0x1: 'Chinese',
            0x2: 'English',
        }.get(language_code, 'Unknown')

        print("""
GPO: {}
GPI: {}
GPS Status: {}
Alarm (1): {}
Alarm (2): {}
Charge: {}
Active: {}
Language: {}
            """.format(
                gpo, gpi, gps_status, alarms_1, alarms_2, charge, active, language
            )
        )

    def handle_message_type(self, t, data):
        handlers = {
            0x01: self.login,
            0x12: self.location,
            0x13: self.heartbeat,
        }
        handler = handlers.get(t, self.unknown_packet_type)
        handler(t, data)

    def process_message(self, data):
        try:
            start_code, = unpack('h', data[:2])
            if start_code != 0x7878:
                print('Invalid start code {}'.format(start_code))
                return

            header = data[2:4]
            body = data[4:-4]
            footer = data[-4:]
            checksummable_data = data[2:-2]
            self.length, packet_type = unpack('BB', header)
            self.serial, error_check = unpack('!HH', footer)
            if calc_crc(checksummable_data) != error_check:
                print('Checksum failure')
                return

            self.handle_message_type(packet_type, body)
        except error as e:
            print('Error:', e)
            return

    def handle(self):
        self.request.settimeout(READ_TIMEOUT_SECS)
        data = b''
        connectDB()
        while True:
            try:
                buf = self.rfile.readline()
            except socket.timeout as e:
                print('Timed out')
                break
            if not len(buf):
                print('Disconnected')
                break
            data += buf
            if data.endswith(b'\r\n'):
                self.process_message(data.strip())
                data = b''
        disconnectDB()


if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 6780

    initDB()

    server = GPSServer((HOST, PORT), GP06)
    server.serve_forever()

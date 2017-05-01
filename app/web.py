#!/usr/bin/env python3

from datetime import datetime, timedelta
from flask import Flask, request, render_template

from models import Device, Position

app = Flask(__name__)


@app.route('/')
def hello():
    return "Nothing to see here!"


@app.route('/vanloc/')
def van_loc():
    try:
        last_posn = Position.select().order_by(Position.timestamp.desc()).get()
    except Position.DoesNotExist:
        return 'No data logged yet!'
    day_ago = datetime.now() - timedelta(hours=24)
    track = (
        Position
        .select()
        .where(Position.timestamp > day_ago)
        .order_by(Position.timestamp)
    )
    return render_template(
        'position.html',
        position=last_posn,
        track=track
    )


@app.route('/iamat/', methods=['POST'])
def log_position():
    device = request.form.get('device')
    lat = request.form.get('lat')
    lon = request.form.get('lon')
    speed = request.form.get('speed')
    course = request.form.get('course')
    if (
        device is None or
        lat is None or
        lon is None
    ):
        return 'Missing required arg'

    print('Device {}: ({}, {}) {} @ {}'.format(
        device,
        lat, lon,
        speed, course
    ))
    device, created = Device.get_or_create(
        device_id=device
    )
    device.log_position(
        Position(
            num_sats=None,
            timestamp=datetime.now(),
            longitude=lon,
            latitude=lat,
            speed=speed,
            course=course
        )
    )
    return 'OK'

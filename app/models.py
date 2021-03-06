from peewee import (
    PostgresqlDatabase, Model, ForeignKeyField, IntegerField, DateTimeField,
    FloatField, CharField
)

db = PostgresqlDatabase('vt', user='vt')

conncount = 0


class VTModel(Model):
    class Meta:
        database = db


class Device(VTModel):
    device_id = CharField()

    def log_position(self, position):
        position.device = self
        position.save()


class Position(VTModel):
    device = ForeignKeyField(Device, related_name='positions')
    num_sats = IntegerField(null=True)
    timestamp = DateTimeField()
    longitude = FloatField()
    latitude = FloatField()
    speed = FloatField(null=True)
    course = FloatField(null=True)


def initDB():
    db.create_tables([Device, Position], True)


def connectDB():
    print("Connecting to DB")
    db.connect()
    global conncount
    conncount += 1
    print("ConnCount is", conncount)


def disconnectDB():
    print('Disconnecting from DB')
    print('Closing:', db.close())
    global conncount
    conncount -= 1
    print("ConnCount is", conncount)

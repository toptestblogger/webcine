import json

from models import TranscodingSettings, Media, TranscodedMedia
import pika
import os

connection = pika.BlockingConnection(pika.ConnectionParameters(
    host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='transcode', durable=True)


def create_transcode_task(media, settings):
    tm = TranscodedMedia.create(media=media, settings=settings)

    target_file = 'storage/transcoded/{}/{}.mkv'.format(settings.id, media.id)
    if not os.path.isdir(os.path.dirname(target_file)):
        os.makedirs(os.path.dirname(target_file))

    task = {
        'id': tm.id,
        'file': media.path,
        'codec': settings.codec,
        'target': target_file
    }
    task.update(json.loads(settings.settings))
    task = json.dumps(task)

    channel.basic_publish(exchange='', routing_key='transcode', body=task.encode(),
                          properties=pika.BasicProperties(delivery_mode=2))


def finished_transcode_task(id):
    tm = TranscodedMedia.get(TranscodedMedia.id == id)
    tm.done = True
    tm.save()


def transcode_one(id):
    media = Media.get(Media.id == id)
    for setting in TranscodingSettings.select():
        print("Transcode {} to {}".format(media.name, setting.label))

        create_transcode_task(media, setting)


def create_transcode_tasks():
    settings = list(TranscodingSettings.select())
    for media in Media.select():
        for setting in settings:
            try:
                TranscodedMedia.get(media == media, settings == setting)
            except:
                print("Transcode {} to {}".format(media.name, setting.label))
                create_transcode_task(media, setting)
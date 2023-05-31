from telethon import TelegramClient, connection
from telethon.tl.types import InputMessagesFilterVideo, DocumentAttributeFilename
import hypercorn.asyncio
from quart import Quart, request, render_template, send_file, abort
import json
import os

#load db
f = open('db.json')
db = json.load(f)
f.close()

#use telegram 
client = TelegramClient('signin', db['app']['telegram']['api_id'], db['app']['telegram']['api_hash'])

#api url
private_api_url = "/api/{}".format(db['auth']['token'])

#use quart
app = Quart(__name__)
app.debug = True

#quart telegram config
@app.before_serving
async def startup():
    await client.connect()

@app.after_serving
async def cleanup():
    await client.disconnect()

#index
@app.route('/', ['GET'])
async def index():
    return await render_template('web.html')

#test login
@app.route('{}/login_alert'.format(private_api_url))
async def loginAlert():
    await client.send_message('me', 'New Login')
    return {
        'ok': "true"
    }

#get auth token
@app.route('/api/get_token')
async def getToken():
    username = request.args.get('username')
    password = request.args.get('password')
    if username == db['auth']['username'] and password == db['auth']['password']:
        return {
            'token': db['auth']['token']
        }
    return {
        'ok': "false"
    }

#get medias
@app.route('{}/get_files/<int:limit>/<int:offset>'.format(private_api_url))
async def getFiles(limit = 10, offset = 0):
    data =await client.get_messages(
        db['app']['telegram']['disk_channel'], 
        limit = limit,
        add_offset = offset,
        filter = InputMessagesFilterVideo
    )
    messages = []
    for msg in data:
        filename = ""
        try:
            for attr in msg.media.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    filename = attr.file_name
        except:
            pass
        messages.append({
            'id': msg.id,
            'filename': filename,
            'size': msg.media.document.size,
            'type': msg.media.document.mime_type,
            'message': msg.message,
            'time': str(msg.date)
        })
    return {
        'total': len(messages),
        'files': messages
    }
    
    
#file info
@app.route('{}/fileinfo/<int:file_id>'.format(private_api_url), methods=['GET'])
async def fileinfo(file_id):
    data = await client.get_messages(db['app']['telegram']['disk_channel'], ids = file_id)
    if data.media == None:
        return {
            'ok': "false"
        }
    filename = ""
    try:
        for attr in data.media.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name
    except:
        pass 
    return {
        'id': file_id,
        'filename': filename,
        'size': data.media.document.size,
        'type': data.media.document.mime_type,
        'message': data.message,
        'time': data.date
    }

#download file
@app.route('/api/download/<int:file_id>', methods=['GET'])
async def Download(file_id):
    path = "disk/{}.mp4".format(file_id)
    try:
        if not os.path.exists(path):
            file = await client.get_messages(db['app']['telegram']['disk_channel'], ids = file_id)
            await file.download_media(path)
        return await send_file(path)
    except:
        pass
    abort(404)

#serve app
async def main():
    await hypercorn.asyncio.serve(app, hypercorn.Config())

if __name__ == '__main__':
    client.loop.run_until_complete(main())
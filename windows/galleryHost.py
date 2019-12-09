import os
import time
import subprocess
import shutil
import requests
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import storage
import secret.gfycatSecrets as gfycatAuth

# LOCAL VARIABLES
STORAGE = r"F:\mocapMath\Sandbox\host"
BLEND = os.path.join(STORAGE, "markers.blend")
bat = os.path.join(STORAGE, "blender.bat") # Adjust .bat to point at blender installation
pyBlender = os.path.join(STORAGE, "importRender.py")

# Authorize Firebase
cred = credentials.Certificate('secret/mocapBoston.json')
firebase_admin.initialize_app(cred, {'storageBucket': 'mocapboston.appspot.com'})
firestoreDatabase = firestore.client()
COLLECTION = firestoreDatabase.collection(u'dev')
BUCKET = storage.bucket()

def authorizeGfycat():
    body = {
        "grant_type":"password",
        "client_id" : gfycatAuth.CLIENT_ID,
        "client_secret" : gfycatAuth.CLIENT_SECRET,
        "username" : gfycatAuth.USERNAME,
        "password" : gfycatAuth.PASSWORD
    }

    token = requests.post("https://api.gfycat.com/v1/oauth/token", json=body, timeout=3).json()
    access_token = token["access_token"]
    auth_header = {"Authorization" : "Bearer {}".format(access_token)}

    return auth_header

def processCapture(sessionID):
    workingDir = os.path.join(STORAGE, sessionID)
    os.mkdir(workingDir)
    blob = BUCKET.blob(sessionID)
    blob.download_to_filename(os.path.join(workingDir, "solve.mocap"))
    print("Downloaded {}".format(os.path.join(workingDir, "solve.mocap")))

    blendCopy = os.path.join(workingDir, "{}.blend".format(sessionID))
    shutil.copyfile(BLEND, blendCopy)
    subprocess.run([bat, blendCopy, pyBlender])

    # GfyCat

    gfyInfo = {
        "title" : "mocapBoston | {}".format(sessionID.upper()),
        "description" : "A visualization of a motion capture performance created at mocapBoston.",
        "noMd5" : True
    }
    authorization = authorizeGfycat()
    upload = requests.post("https://api.gfycat.com/v1/gfycats", json=gfyInfo, headers=authorization)
    gfyID = upload.json().get("gfyname")

    if gfyID:
        with open(os.path.join(workingDir, "render.mp4"), "rb") as payload:
            code = requests.put("https://filedrop.gfycat.com/{}".format(gfyID), payload)
            print("Uploaded to Gfycat with Status {}".format(code.status_code))
        return gfyID

    return False

def snapshotUpdate(snapshot, update, readTime):
    for document in snapshot:
        sessionID = document.id
        print("Processing {}".format(sessionID))
        gfy = processCapture(sessionID)
        COLLECTION.document(sessionID).update({
            u'gifID' : gfy,
            u'processed' : True
        })
        print("Processed {}".format(sessionID))

query = COLLECTION.where(u'solved', u"==", True).where(u'processed', u'==', False)
watcher = query.on_snapshot(snapshotUpdate)

while True:
    time.sleep(1)

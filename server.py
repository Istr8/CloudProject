from flask import Flask, render_template, request, url_for, flash, redirect
import os
from azure.storage.blob import BlobServiceClient
from translate import Translator
from zipfile import ZipFile
import shutil
from werkzeug.utils import secure_filename
import io

UPLOAD_FOLDER = 'static/uploads'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
blob_service_client = BlobServiceClient.from_connection_string(connect_str)

app.config['SECRET_KEY'] = 'your secret key'

messages = [{'title': 'Message One',
             'content': 'Message One Content'},
            {'title': 'Message Two',
             'content': 'Message Two Content'}
            ]

cereri = {'i': 0}


@app.route('/')
def index():
    return render_template('index.html', messages=messages)


def sendToBlob(file, email):

    cereri['i'] += 1
    blob_client = blob_service_client.get_blob_client(
        container="traduceri", blob=file.filename)
    blob_client.upload_blob(file)

    blob_client2 = blob_service_client.get_blob_client(
        container="traduceri", blob=f"email{cereri['i']}")
    blob_client2.upload_blob(email)


def download(file):

    download_file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    container_client = blob_service_client.get_container_client(
        container="traduceri")
    print("\nDownloading blob to \n\t" + download_file_path)

    blob_list = container_client.list_blobs()

    for blob in blob_list:
        print("\t" + blob.name)
        if (file.filename in blob.name):
            with open(file=download_file_path, mode="wb") as download_file:
                download_file.write(
                    container_client.download_blob(blob.name).readall())

    download_zip = ZipFile(download_file_path, 'r')
    download_zip.extractall(UPLOAD_FOLDER)


def tradu():
    folder = os.listdir(os.path.join(UPLOAD_FOLDER, 'fisier'))
    for nume_fisier in folder:
        path = os.path.join(UPLOAD_FOLDER, 'fisier' + '/' + nume_fisier)
        fisier = open(path, 'r')
        if nume_fisier == 'limba1.txt':
            from_lang = fisier.read().rstrip()
            fisier.close()
        elif nume_fisier == 'limba2.txt':
            to_lang = fisier.read().rstrip()
            fisier.close()
            break

    translator = Translator(from_lang=from_lang, to_lang=to_lang)

    folder_nou = os.path.join(UPLOAD_FOLDER, f"traduse{cereri['i']}")
    mode = 0o666

    os.mkdir(folder_nou, mode)

    for nume_fisier in folder:
        if nume_fisier != 'limba1.txt' and nume_fisier != 'limba2.txt':
            path = os.path.join(UPLOAD_FOLDER, 'fisier' + '/' + nume_fisier)
            fisier = open(path, 'r',  encoding='utf-8')
            text = fisier.read().rstrip()
            print(text)
            translation = translator.translate(text)
            fisier.close()
            new_path = folder_nou + '\\' + nume_fisier
            fisier_nou = open(new_path, "w")
            fisier_nou.write(translation)
            fisier_nou.close()

    shutil.make_archive(folder_nou, 'zip', folder_nou)


# Create a blob client using the local file name as the name for the blob
    blob_client3 = blob_service_client.get_blob_client(
        container="traduceri", blob=f"traduse{cereri['i']}.zip")

    print("\nUploading to Azure Storage as blob:\n\t" + "traduse.zip")

    # Upload the created file
    with open(file=os.path.join(UPLOAD_FOLDER, f"traduse{cereri['i']}.zip"), mode="rb") as data:
        blob_client3.upload_blob(data)


@ app.route('/create/', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        email = request.form['email']
        file = request.files['myfile']

        if not email:
            flash('Email is required!')
        elif not file:
            flash('File is required!')
        else:
            messages.append({'title': email, 'content': 'abc'})
            sendToBlob(file, email)
            download(file)
            tradu()
            return redirect(url_for('index'))

    return render_template('create.html')

import os
import re
from flask_sqlalchemy import SQLAlchemy
import json
from flask import Flask, jsonify, flash, request, redirect, url_for, render_template, send_from_directory
from PIL import Image
from werkzeug.utils import secure_filename
import importlib.util
import sys
from decouple import config
from models import RackLocation, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# from image_processing_new import fubar_master_function
sys.path.append('/home/ubuntu/fubar')
from image_processing_new import fubar_master_function

UPLOAD_FOLDER = '/home/ubuntu/fubar/flask/uploads'
# UPLOAD_FOLDER = '/home/ubuntu/fubar/flask/static/uploads'

POSTGRES = {
    'user': config('DATABASE_USER'),
    'pw': config('DATABASE_PASSWORD'),
    'db': config('DATABASE_NAME'),
    'host': config('DATABASE_HOST'),
    'port': '5432',
}


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = b'-I\xd9I\xa0\xe7R\x83Q\xc0\xce\xf2\xe4\xc8\x020'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:\
%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg',])


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def front_page():
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            myvar =  request.form['coordinates']
            myvar = json.loads(myvar)
            print(myvar)
            if myvar != 0:
                lng = myvar[0]
                lat = myvar[1]
                print("lng: " + str(myvar[0]) +  "lat: " + str(myvar[1]))
            else:
                print("photo came from desktop")
#           im = Image.open(path)
            #im.save(path)
            drawpath = os.path.join(app.config['UPLOAD_FOLDER'], 'draw.jpg')
            global pred
            pred = fubar_master_function(path, outfile_draw=drawpath)
            print(pred)
            global message
            message = 'were detected'
            print("id: ", rack_location.id)
            objects = pred[1]
            d = {x:objects.count(x) for x in objects}

            if 'rack' in d and myvar != 0:
                racks =d['rack']
                loc = f'POINT({lng} {lat})'
		rack_location = RackLocation(
                location=loc, numracks=racks)
                session.add(rack_location)
                session.commit()
                session.refresh(rack_location)
            if objects:
                message = 'were detected'
                classes = 0
                if d:
                    for i in d:
                        classes += 1
                        if d[i] == 1:
                           detected = str(d[i]) + ' ' + i
                           if classes > 1:
                               message = ' '.join((detected, 'and', message))
                           else:
                               message = ' '.join((detected, message))
                        else:
                           detected = str(d[i]) + ' ' + i + 's'
                           if classes > 1:
                               message = ' '.join((detected, 'and',  message))
                           else:
                               message = ' '.join((detected, message))

            else:
                message = 'Nothing was detected, please try again'

            global objs
            objs = len(objects)

            return redirect(url_for('uploaded_file',
                                    filename=filename))
    # else:
    #     return redirect(url_for('front_page'))

@app.route('/upload/<filename>')
def send_file(filename):
    # path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    # render_template("photo_sent.html",
    #             drawpath=path,
    #             draw_image=
    #         )

@app.route('/show/<filename>')
def uploaded_file(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    drawpath = os.path.join(app.config['UPLOAD_FOLDER'], 'draw.jpg')
    return render_template('photo_sent.html', path=path, drawpath=drawpath, objs=objs, filename=filename, pred=pred, message=message)


@app.route('/data')
def names():
    data = {"names": ["John", "Jacob", "Julie", "Jennifer", "Satan"]}
    return jsonify(data)


if __name__ == '__main__':
    # app.debug = True
    app.run(host='0.0.0.0')

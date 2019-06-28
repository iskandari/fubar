import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from flask_appbuilder import Model
from geoalchemy2 import Geometry

class RackLocation(Model):
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow) 
    location = Column(Geometry('POINT'), nullable=True)
    numracks = Column(Integer, default=0)

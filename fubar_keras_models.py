from keras.applications.inception_v3 import InceptionV3
from keras.layers import GlobalAveragePooling2D, Dense
from keras.preprocessing import image
from keras.models import Model
from keras.preprocessing.image import ImageDataGenerator
from keras.callbacks import History
# from keras_metrics import recall, precision

import matplotlib
matplotlib.use('TkAgg')

from pathlib import Path

import PIL
import os
import numpy as np
import glob
import pandas as pd

import neptune as npt

from cnn_toolkit import Precision, Recall, filepattern, NeptuneMonitor, \
    pool_generator_classes, show_architecture, frosty, DebuggingCallback, \
    file_train_test_split

from npt_token_file import project_path, api
npt_token = api
npt_project = project_path

# -----------------------------
# OPTIONAL: INITIALIZE NEPTUNE |
# -----------------------------
# npt.init(api_token=npt_token,
#          project_qualified_name=npt_project)
# npt.create_experiment(upload_source_files=[])  # keep what's inside parentheses to prevent neptune from reading code

# -----------
# BASE MODEL |
# -----------
base = InceptionV3(weights='imagenet', include_top=False)
# ---------------------------------------------------------------------------------------------------------------------


# ----------------
# HYPERPARAMETERS |
# ----------------
INPUT_H = 280
INPUT_W = 280
BATCH_SIZE = 32
TRAIN_SIZE = ((124+91+24+25) * 8) // 10
TEST_SIZE = ((124+91+24+25) * 2) // 10
EPOCHS = 1
# ---------------------------------------------------------------------------------------------------------------------

# ---------------------
# HERE LIVE THE IMAGES |
# ---------------------

path_to_archive = Path.home() / Path('Downloads/FubarArchive/')

# ---------------------------------------------------------------------------------------------------------------------

# -------------------
# DATA PREPROCESSING |
# -------------------
# We need a random split of 80/20 for training and validation images. Make a DF mapping files from random categories
# to a validation or training set and use it to construct training_generator and validation_generator

paths = file_train_test_split(path_to_archive, ['*.jpg', '*.jpeg', '*.png'])

test_image_datagen = ImageDataGenerator(
        rescale=1./255)

training_image_datagen = ImageDataGenerator(
        rescale=1./255,
        shear_range=0.2,
        zoom_range=0.4,
        horizontal_flip=True)

training_generator = training_image_datagen.flow_from_dataframe(
                paths[0],
                x_col='x_col',
                y_col='y_col',
                target_size=(INPUT_H, INPUT_W),
                batch_size=BATCH_SIZE,
                class_mode='sparse')

validation_generator = test_image_datagen.flow_from_dataframe(
                paths[1],
                x_col='x_col',
                y_col='y_col',
                target_size=(INPUT_H, INPUT_W),
                batch_size=BATCH_SIZE,
                class_mode='sparse')

# Pool classes to exclude U-bar/LoopLock differentiation for the first model
class_pool_mapping = {0: 0, 1: 0, 2: 1, 3: 1}
pool_generator_classes(training_generator, class_pool_mapping)
pool_generator_classes(validation_generator, class_pool_mapping)


# ---------------------------------------------------------------------------------------------------------------------


# -------------------
# MODEL ARCHITECTURE |
# -------------------
y = base.output
y = GlobalAveragePooling2D()(y)  # __call__()
y = Dense(1024, activation='relu', name='my_dense_1024')(y)
y_pred = Dense(2, activation='sigmoid', name='output_dense')(y)
# ---------------------------------------------------------------------------------------------------------------------


# -------------------------------
# CREATE MODEL FROM ARCHITECTURE |
# -------------------------------
model = Model(inputs=base.input, outputs=y_pred)
# tf.Tensor objects are associated with tf.Graph object, which stores the architecture of the model,
# that's why for functional Keras Model object all we need to do is specify the input and output tensor
# and Model object figures the actual architecture from tf.Graph
# ---------------------------------------------------------------------------------------------------------------------

# --------------
# FREEZE LAYERS |
# --------------
frosty(base.layers)  # this will freeze all base model layers
# ---------------------------------------------------------------------------------------------------------------------

# -----------------------------------
# COMPILE MODEL AND SET UP CALLBACKS |
# -----------------------------------
# always compile model AFTER layers have been frozen

model.compile(optimizer='rmsprop', loss='sparse_categorical_crossentropy', metrics=['acc', 'mae'])
precision = Precision()
recall = Recall()  # fixme - this is YIELDING TUPLES (images, labels) NOT RETURNING ONES!!
history = History()
# deb = DebuggingCallback()
npt_monitor = NeptuneMonitor(BATCH_SIZE)
# ---------------------------------------------------------------------------------------------------------------------


# ---------------------------------------------
# TRAIN TOP LAYERS ON NEW DATA FOR A FEW EPOCHS|
# ---------------------------------------------
model.fit_generator(training_generator,
                    steps_per_epoch=(TRAIN_SIZE / BATCH_SIZE),  # number of samples in the dataset
                    epochs=EPOCHS,  # number of epochs, training cycles
                    validation_data=validation_generator,  # performance eval on test set
                    validation_steps=(TEST_SIZE / BATCH_SIZE),
                    callbacks=[history,
                               # precision])
                               recall])
                               # deb])
                               # npt_monitor])
# read on SO, that the right way to compute precision and recall is to do it at the end of each epoch
# thus we use precision and recall functions as callbacks
# ---------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------
# VISUALIZE BASE ARCHITECTURE TO DECIDE WHICH LAYERS TO FREEZE |
# -------------------------------------------------------------
print(show_architecture(base))
# INSERT DEBUGGER BREAKPOINT DIRECTLY ON THE NEXT COMMAND TO VIEW THE ARCHITECTURE AT RUNTIME
# ---------------------------------------------------------------------------------------------------------------------

# ------------------------
# STOP NEPTUNE EXPERIMENT |
# ------------------------
# npt.stop()

# ======================================================================================================================
# ======================================================================================================================

# --------------
# FREEZE LAYERS |
# --------------
# for now I just pass a slice of layers used in Keras documentation
frosty(model.layers[:249], frost=True)
frosty(model.layers[249:], frost=False)

# -----------------------------
# OPTIONAL: INITIALIZE NEPTUNE |
# -----------------------------
npt.init(api_token=npt_token,
         project_qualified_name=npt_project)
npt.create_experiment(upload_source_files=[])  # keep what's inside parentheses to prevent neptune from reading code
npt_monitor = NeptuneMonitor(BATCH_SIZE)


# ------------------------------------
# COMPILE MODEL AGAIN AND TRAIN AGAIN |
# ------------------------------------
# always compile model AFTER layers have been frozen
model.compile(optimizer='rmsprop', loss='sparse_categorical_crossentropy', metrics=['acc', 'mae'])
model.fit_generator(training_generator,
                    steps_per_epoch=(TRAIN_SIZE / BATCH_SIZE),  # number of samples in the dataset
                    epochs=EPOCHS,  # number of epochs, training cycles
                    validation_data=validation_generator,  # performance eval on test set
                    validation_steps=(TEST_SIZE / BATCH_SIZE),
                    callbacks=[history,
                               precision,
                               recall,
                               npt_monitor])

# --------------------------------------
# EXPORT MODEL ARCHITECTURE AND WEIGHTS |
# --------------------------------------
# export model structure to json file:
model_struct_json = model.to_json()
filename = filepattern('model_ana_', '.json')
with open(filename, 'w') as f:
    f.write(model_struct_json)

# export weights to an hdf5 file:
w_filename = filepattern('weights_ana_', '.h5')
model.save_weights(w_filename)

# ---------------------------------------------------------------------------------------------------------------------

# ------------------------
# STOP NEPTUNE EXPERIMENT |
# ------------------------
npt.stop()
# ======================================================================================================================
# ======================================================================================================================

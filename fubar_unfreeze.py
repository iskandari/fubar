from tensorflow.python.keras.callbacks import History
import matplotlib
import neptune as npt
import tensorflow as tf
import os

from cnn_toolkit import filepattern, NeptuneMonitor, \
    frosty, get_fresh_weights_and_model, \
    make_pred_output_callback
from fubar_preprocessing import training_generator, validation_generator
from fubar_CONF import hprm

from npt_token_file import project_path, api

matplotlib.use('TkAgg')
npt_token = api
npt_project = project_path

# -----------------------------
# OPTIONAL: INITIALIZE NEPTUNE |
# -----------------------------
npt.init(api_token=npt_token,
         project_qualified_name=npt_project)
npt.create_experiment(upload_source_files=[])  # keep what's inside parentheses to prevent neptune from reading code

# ----------------
# HYPERPARAMETERS |
# ----------------
print(hprm)
# ---------------------------------------------------------------------------------------------------------------------


# ----------------
# RE-CREATE MODEL |
# ----------------
m, w = get_fresh_weights_and_model(os.getcwd(), 'model_allfreeze_*', 'weights_allfreeze_*')
with open(m, 'r') as f:
    model = tf.keras.models.model_from_json(f.read())
model.load_weights(w)
# ---------------------------------------------------------------------------------------------------------------------

history = History()
npt_monitor = NeptuneMonitor(hprm['BATCH_SIZE'])
# ---------------------------------------------------------------------------------------------------------------------

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
npt_monitor = NeptuneMonitor(hprm['BATCH_SIZE'])


# ------------------------------------
# COMPILE MODEL AGAIN AND TRAIN AGAIN |
# ------------------------------------
# always compile model AFTER layers have been frozen
recall = tf.keras.metrics.Recall()
precision = tf.keras.metrics.Precision()
early_stopping = tf.keras.callbacks.EarlyStopping(monitor='val_loss',
                                                  min_delta=hprm['EARLY_STOPPING_DELTA'],
                                                  patience=0,
                                                  verbose=0,
                                                  mode='auto',
                                                  baseline=None,
                                                  restore_best_weights=True)
validation_output_callback = tf.keras.callbacks.LambdaCallback(on_epoch_end=make_pred_output_callback(
    model,
    validation_generator,
    hprm['BATCH_SIZE']))

model.compile(optimizer='rmsprop', loss='binary_crossentropy', metrics=['acc',
                                                                        recall,
                                                                        precision])
post_training_model = model.fit_generator(training_generator,
                                          steps_per_epoch=(hprm['TRAIN_SIZE'] / hprm['BATCH_SIZE']),  # number of samples in the dataset
                                          epochs=hprm['EPOCHS'],  # number of epochs, training cycles
                                          validation_data=validation_generator,  # performance eval on test set
                                          validation_steps=(hprm['TEST_SIZE'] / hprm['BATCH_SIZE']),
                                          callbacks=[history,
                                                     npt_monitor])
                                                     # validation_output_callback])
                                                    # early_stopping])

# --------------------------------------
# EXPORT MODEL ARCHITECTURE AND WEIGHTS |
# --------------------------------------
# export model structure to json file:
model_struct_json = model.to_json()
filename = filepattern('model_partfreeze_', '.json')
with open(filename, 'w') as f:
    f.write(model_struct_json)

# export weights to an hdf5 file:
w_filename = filepattern('weights_partfreeze_', '.h5')
model.save_weights(w_filename)

# ---------------------------------------------------------------------------------------------------------------------

# ------------------------
# STOP NEPTUNE EXPERIMENT |
# ------------------------
npt.stop()
# ======================================================================================================================
# ======================================================================================================================

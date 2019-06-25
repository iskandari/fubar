# Adapted from https://gist.github.com/eavidan/07928337e2859bf8fa607f5693ee4a89#file-tensorflow_serving_rest_client-py

from cnn_toolkit import image_bytestring, load_byte_img
from fubar_preprocessing import hprm
import numpy as np
import requests

# host = 'localhost'
# port = '8501'
# batch_size = 1
# model_name = 'fubar'
# model_version = '4'
# signature_name = 'serving_default'


def tf_serving_predict(image_path,
                       host,
                       port=8501,
                       model_name='fubar',
                       model_version='4',
                       batch_size=1,
                       signature_name='serving_default'):
    """
    function placing calls to the TF Serving Model through REST-API interface
    :param image_path: path to inference image
    :param host: host address of server with exposed API port
    :param port: API port, default is 8501
    :param model_name: string, model name, default is 'fubar'
    :param model_version: integer, denotes currently served model version
    :param batch_size: batch_size of photos, default is 1
    :param signature_name:
    :return:
    """
    image = load_byte_img(image_bytestring(image_path), hprm['INPUT_H'], hprm['INPUT_W'])
    batch = np.repeat(image, batch_size, axis=0).tolist()

    request = {
        "signature_name": signature_name,
        "instances": batch
    }
    response = requests.post(f"http://{host}:{port}/v1/models/{model_name}/versions/{model_version}:predict",
                             json=request)
    # response = requests.post(f"http://localhost:8501/v1/models/fubar/versions/4:predict", json=request)
    result = response.json()
    return result

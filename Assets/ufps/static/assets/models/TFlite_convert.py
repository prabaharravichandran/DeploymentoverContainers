import tensorflow as tf

model = tf.keras.models.load_model("/gpfs/fs7/aafc/phenocart/PhenomicsProjects/DeploymentoverContainers/Assets/ufps/static/assets/models/maturity.h5",
                                   custom_objects = {"mse": tf.keras.losses.MeanSquaredError()
                                                     })
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

with open("yield.tflite", "wb") as f:
    f.write(tflite_model)

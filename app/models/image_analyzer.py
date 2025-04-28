import tensorflow as tf
import numpy as np
from PIL import Image
import io

class ImageAnalyzer:
    def __init__(self):
        """
        Initialise le modèle de détection d'objets
        """
        # Chargement du modèle MobileNetV2 pré-entraîné
        self.model = tf.keras.applications.MobileNetV2(
            weights='imagenet',
            include_top=True,
            input_shape=(224, 224, 3)
        )
        
        # Chargement des classes ImageNet
        self.classes = tf.keras.applications.mobilenet_v2.decode_predictions(
            np.zeros((1, 1000)), top=1000
        )[0]

    def preprocess_image(self, image_bytes):
        """
        Prétraite l'image pour le modèle
        """
        # Conversion des bytes en image PIL
        image = Image.open(io.BytesIO(image_bytes))
        
        # Redimensionnement à 224x224
        image = image.resize((224, 224))
        
        # Conversion en array numpy
        img_array = np.array(image)
        
        # Prétraitement spécifique à MobileNetV2
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
        
        # Ajout d'une dimension pour le batch
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array

    def analyze_image(self, image_bytes):
        """
        Analyse l'image et retourne les prédictions
        """
        # Prétraitement de l'image
        processed_image = self.preprocess_image(image_bytes)
        
        # Prédiction
        predictions = self.model.predict(processed_image)
        
        # Décodage des prédictions
        decoded_predictions = tf.keras.applications.mobilenet_v2.decode_predictions(
            predictions, top=5
        )[0]
        
        # Formatage des résultats
        results = [
            {
                "class": pred[1],  # nom de la classe
                "confidence": float(pred[2])  # confiance
            }
            for pred in decoded_predictions
        ]
        
        return results 
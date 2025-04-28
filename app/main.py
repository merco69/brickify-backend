from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from .models.image_analyzer import ImageAnalyzer

app = FastAPI(
    title="Brickify AI API",
    description="API pour la transformation d'images en modèles LEGO",
    version="1.0.0"
)

# Initialisation du modèle
image_analyzer = ImageAnalyzer()

@app.get("/status")
async def get_status():
    """
    Endpoint de vérification de l'état de l'API
    """
    return {"message": "API OK"}

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Endpoint pour analyser une image
    """
    try:
        # Lecture du fichier
        contents = await file.read()
        
        # Analyse de l'image
        results = image_analyzer.analyze_image(contents)
        
        return JSONResponse(content={
            "message": "Analyse réussie",
            "predictions": results
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Erreur lors de l'analyse : {str(e)}"}
        ) 
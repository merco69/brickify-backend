import asyncio
import json
from pathlib import Path
from services.blocky_service import BlockyService

async def test_conversion():
    # Initialisation du service
    service = BlockyService()
    
    # Chemin vers le modèle de test
    model_path = Path(__file__).parent / "test_models" / "cube.obj"
    
    print(f"Testing conversion of {model_path}")
    
    try:
        # Conversion du modèle
        result = await service.convert_to_lego(str(model_path))
        
        # Affichage des résultats
        print("\nConversion successful!")
        print(f"Model info: {json.dumps(result['model_info'], indent=2)}")
        print(f"\nNumber of layers: {len(result['instructions'])}")
        print(f"Using device: {result['device']}")
        print(f"CUDA available: {result['cuda_available']}")
        
        # Affichage des détails de la première couche
        if result['instructions']:
            first_layer = result['instructions'][0]
            print(f"\nFirst layer details:")
            print(f"Layer number: {first_layer['layer']}")
            print(f"Number of bricks: {len(first_layer['bricks'])}")
            print("Brick positions and sizes:")
            for brick in first_layer['bricks']:
                print(f"  Position: {brick['position']}, Size: {brick['size']}")
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_conversion()) 
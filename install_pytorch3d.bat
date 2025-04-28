@echo off
echo Installation de PyTorch3D...

REM Vérifier si conda est installé
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo Conda n'est pas installé. Veuillez installer Miniconda ou Anaconda.
    exit /b 1
)

REM Créer un environnement conda
conda create -n brickify python=3.9 -y
conda activate brickify

REM Installer les dépendances
conda install pytorch torchvision cudatoolkit=11.3 -c pytorch -y
conda install -c fvcore -c iopath -c conda-forge fvcore iopath -y
conda install -c bottler nvidiacub -y

REM Cloner et installer PyTorch3D
git clone https://github.com/facebookresearch/pytorch3d.git
cd pytorch3d
python setup.py install

echo Installation terminée !
echo Pour activer l'environnement : conda activate brickify 
#!/bin/bash

SPARK_SUBMIT=${1:-spark-submit}
SCRIPT_PATH="./spark-streaming/log_analyzer.py"

clean_dir() {
    if [ -d "$1" ]; then
        echo "Suppression du répertoire : $1"
        rm -rf "$1"
    else
        echo "Environnement déjà propre"
    fi

}

echo "Nettoyage de l'environnement"
clean_dir "output/errors"
clean_dir "checkpoint/errors"
echo -e "Lancement du job Spark"
"$SPARK_SUBMIT" "$SCRIPT_PATH"
if [$? -eq 0]; then
    echo "Job Spark terminé sans erreur"
else
    echo "Echec durant l'exécution du job Spark"
    exit 1
fi
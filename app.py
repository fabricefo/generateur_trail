from flask import Flask, render_template, request, redirect, url_for
import os
import pandas as pd
from generator import lire_trace_gpx, calcul_etapes, calculer_nb_semaines, generer_plan, ajouter_resume_hebdo, export_pdf_plan, haversine

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Récupérer le fichier GPX téléchargé
        file = request.files["gpx_file"]
        if file and file.filename.endswith(".gpx"):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            # Lire et analyser le fichier GPX
            points = lire_trace_gpx(filepath)
            distance_totale = sum(haversine(lat1, lon1, lat2, lon2) for (_, lat1, lon1, _), (_, lat2, lon2, _) in zip(points[:-1], points[1:]))
            denivele_positif = sum(max(0, ele2 - ele1) for (_, _, _, ele1), (_, _, _, ele2) in zip(points[:-1], points[1:]))

            # Calculer le nombre de semaines d'entraînement
            nb_semaines = calculer_nb_semaines(distance_totale, denivele_positif)

            # Générer le plan d'entraînement
            plan_df = generer_plan(nb_semaines, "Finir avec plaisir", "2025-06-01", distance_totale, denivele_positif)
            resume_df = ajouter_resume_hebdo(plan_df)

            # Exporter les résultats
            plan_df.to_csv("plan_entraînement.csv", index=False)
            export_pdf_plan(plan_df)

            # Afficher les résultats
            return render_template(
                "results.html",
                distance_totale=round(distance_totale, 2),
                denivele_positif=int(denivele_positif),
                nb_semaines=nb_semaines,
                plan=plan_df.to_dict(orient="records")
            )

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
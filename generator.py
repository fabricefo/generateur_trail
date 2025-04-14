import gpxpy
import pandas as pd
import unicodedata
from datetime import datetime, timedelta
from math import sqrt
from fpdf import FPDF

# === PARAMÈTRES UTILISATEUR ===
fichier_gpx = "Trace_Cassis.gpx"
distance_etape_km = 5
vitesse_plat = 9  # km/h
fatigue_coeff = 1.05
nb_semaines = 8
seances_par_semaine = 4
objectif = "Finir avec plaisir"
date_course = "2025-06-01"

# === FONCTIONS UTILITAIRES ===

def lire_trace_gpx(fichier):
    with open(fichier, 'r') as f:
        gpx = gpxpy.parse(f)
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                points.append((p.time, p.latitude, p.longitude, p.elevation))
    return points

def haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371.0  # Rayon de la Terre
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def calcul_etapes(points, distance_etape_km):
    etapes = []
    d_tot, d_plus, d_moins, temps_total = 0, 0, 0, 0
    dist = 0
    start_idx = 0

    for i in range(1, len(points)):
        t1, lat1, lon1, ele1 = points[i-1]
        t2, lat2, lon2, ele2 = points[i]
        d = haversine(lat1, lon1, lat2, lon2)
        dist += d
        d_tot += d
        d_plus += max(0, ele2 - ele1)
        d_moins += max(0, ele1 - ele2)

        if dist >= distance_etape_km:
            effort = dist + (d_plus / 100) * 0.8
            vitesse = vitesse_plat * (1 / (1 + d_plus / 500))
            temps_h = effort / vitesse * fatigue_coeff
            temps_total += temps_h

            etapes.append({
                "Étape": len(etapes) + 1,
                "Distance (km)": round(dist, 2),
                "D+ (m)": int(d_plus),
                "D- (m)": int(d_moins),
                "Temps (min)": int(temps_h * 60),
                "Temps (horaire)": f"{int(temps_h)}h{int((temps_h*60)%60):02d}",
                "Cumul distance (km)": round(d_tot, 2),
                "Cumul temps (horaire)": f"{int(temps_total)}h{int((temps_total*60)%60):02d}"
            })
            dist, d_plus, d_moins = 0, 0, 0

    return pd.DataFrame(etapes)

# === PLAN D’ENTRAÎNEMENT ===

def generer_plan(nb_semaines, seances_semaine, objectif, date_course):
    base_date = datetime.strptime(date_course, "%Y-%m-%d") - timedelta(weeks=nb_semaines)
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    plan = []

    for semaine in range(nb_semaines):
        phase = (
            "générale" if semaine < 2 else
            "spécifique" if semaine < 5 else
            "affûtage" if semaine < 7 else
            "course"
        )

        types_seances = {
            "générale": ["Footing", "PPG / Renfo", "Vélo", "Sortie Longue"],
            "spécifique": ["Seuil", "PPG / Renfo", "VMA", "Sortie Longue", "Vélo"],
            "affûtage": ["Footing", "PPG / Renfo", "Seuil", "Sortie Moyenne"],
            "course": ["Footing", "VMA", "Repos", "Course"]
        }[phase]

        jours_utilisés = 0
        for j in range(7):
            if jours_utilisés >= seances_semaine:
                break
            date = base_date + timedelta(weeks=semaine, days=j)
            jour = jours_semaine[j % 7]
            type_seance = types_seances[jours_utilisés % len(types_seances)]

            contenu = {
                "Footing": "45-60 min allure facile",
                "PPG / Renfo": "30-40 min gainage + renfo",
                "Sortie Longue": f"{90 + semaine * 5} min trail vallonné",
                "Vélo": "1h tranquille ou 45 min home-trainer",
                "Seuil": "2x10 à 3x10 min allure tempo",
                "VMA": "8x45s vite / 45s récup",
                "Sortie Moyenne": "1h sur sentiers, allure confortable",
                "Repos": "Repos complet ou 30 min marche",
                "Course": "Jour J ! Donne tout 😉"
            }.get(type_seance, "Footing 45 min")

            conseil = {
                "Footing": "Relâchement et aisance",
                "PPG / Renfo": "Posture, contrôle",
                "Sortie Longue": "Hydrate-toi bien",
                "Vélo": "Cadence souple, récup",
                "Seuil": "Tiens l’allure, respire",
                "VMA": "Explosivité, légèreté",
                "Sortie Moyenne": "Bonne foulée, régularité",
                "Repos": "Bien dormir !",
                "Course": "Rappelle-toi pourquoi tu cours"
            }.get(type_seance, "")

            plan.append({
                "Semaine": semaine + 1,
                "Phase": phase,
                "Date": date.strftime("%Y-%m-%d"),
                "Jour": jour,
                "Type": type_seance,
                "Contenu": contenu,
                "Conseil": conseil
            })
            jours_utilisés += 1

    return pd.DataFrame(plan)

# === RÉSUMÉ HEBDOMADAIRE ===

def ajouter_resume_hebdo(plan_df):
    resume = plan_df.groupby(['Semaine', 'Phase'])['Type'].value_counts().unstack().fillna(0).astype(int)
    return resume.reset_index()

# === EXPORT PDF ===
def nettoyer_texte(txt):
    # Remplacer les caractères non ascii ou typographiques
    txt = unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode('ascii')
    return txt

def export_pdf_plan(plan_df, filename="plan_entraînement_resume.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    titre = "Résumé Hebdomadaire du Plan d’Entraînement"
    pdf.cell(200, 10, txt=nettoyer_texte(titre), ln=True, align='C')

    semaines = plan_df['Semaine'].unique()
    for semaine in semaines:
        phase = plan_df[plan_df['Semaine'] == semaine]['Phase'].iloc[0]
        pdf.set_font("Arial", 'B', size=12)
        pdf.cell(200, 10, nettoyer_texte(f"Semaine {semaine} - Phase: {phase}"), ln=True)

        pdf.set_font("Arial", size=10)
        semaine_data = plan_df[plan_df['Semaine'] == semaine]
        for _, row in semaine_data.iterrows():
            line = f"{row['Jour']} {row['Date']}: {row['Type']} - {row['Contenu']} ({row['Conseil']})"
            pdf.multi_cell(0, 8, nettoyer_texte(line))
        pdf.ln(4)

    pdf.output(filename)
    
# === EXÉCUTION ===

points = lire_trace_gpx(fichier_gpx)
df_etapes = calcul_etapes(points, distance_etape_km)
plan_df = generer_plan(nb_semaines, seances_par_semaine, objectif, date_course)
resume_df = ajouter_resume_hebdo(plan_df)

with pd.ExcelWriter("planning_course_et_entrainement.xlsx", engine="xlsxwriter") as writer:
    df_etapes.to_excel(writer, sheet_name="Temps de passage", index=False)
    plan_df.to_excel(writer, sheet_name="Plan Entrainement", index=False)
    resume_df.to_excel(writer, sheet_name="Résumé Hebdo", index=False)

export_pdf_plan(plan_df)
print("✅ Fichiers générés : Excel + PDF")

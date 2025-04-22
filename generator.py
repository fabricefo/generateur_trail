import os
import gpxpy
import pandas as pd
import unicodedata
from datetime import datetime, timedelta
from math import sqrt
from fpdf import FPDF
import locale

locale.setlocale(locale.LC_TIME, "French_France.1252")

# === PARAMÈTRES UTILISATEUR ===

# Répertoire contenant les fichiers GPX
repertoire_gpx = "gpx"

# Lister les fichiers GPX dans le répertoire et extraire les informations
fichiers_gpx = {}
for idx, fichier in enumerate((f for f in os.listdir(repertoire_gpx) if f.lower().endswith(".gpx")), start=1):
    if fichier.endswith(".gpx"):
        chemin_fichier = os.path.join(repertoire_gpx, fichier)

        # Extraire la date de la course à partir du nom du fichier (YYYYmmdd)
        try:
            date_course = datetime.strptime(fichier[:8], "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            date_course = "Date inconnue"
        
        # Lire le fichier GPX pour extraire le nom du parcours depuis la balise <metadata><name>
        with open(chemin_fichier, 'r') as f:
            gpx = gpxpy.parse(f)
            metadata = gpx
            if metadata:
                nom = metadata.name
            else:
                nom = "Nom inconnu"
            
            fichiers_gpx[str(idx)] = {"fichier": chemin_fichier, "nom": nom, "date_course": date_course}

# Demander à l'utilisateur de choisir un fichier GPX
print("Veuillez choisir un fichier GPX :")
for key, value in fichiers_gpx.items():
    print(f"{key}: {value['nom']} ({value['fichier']}) - Date : {value['date_course']}")

choix = input("Entrez le numéro du fichier : ").strip()
while choix not in fichiers_gpx:
    choix = input("Choix invalide. Entrez un numéro valide : ").strip()

# Récupérer le fichier et les informations associées
fichier_gpx = fichiers_gpx[choix]["fichier"]
nom_parcours = fichiers_gpx[choix]["nom"]
date_course = fichiers_gpx[choix]["date_course"]

distance_etape_km = 5
vitesse_plat = 10  # km/h
nb_semaines = 8
seances_par_semaine = 4
objectif = "Finir avec plaisir"


# === FONCTIONS UTILITAIRES ===

def lire_trace_gpx(fichier):
    with open(fichier, 'r') as f:
        gpx = gpxpy.parse(f)
    points = []
    distance_totale = 0
    denivele_positif = 0
    denivele_negatif = 0
    
    for track in gpx.tracks:
        for segment in track.segments:
            for i, p in enumerate(segment.points):
                points.append((p.time, p.latitude, p.longitude, p.elevation))
                if i > 0:
                    # Calcul de la distance et des dénivelés
                    _, lat1, lon1, ele1 = points[i - 1]
                    _, lat2, lon2, ele2 = points[i]
                    distance_totale += haversine(lat1, lon1, lat2, lon2)
                    denivele_positif += max(0, ele2 - ele1)
                    denivele_negatif += max(0, ele1 - ele2)

    # Afficher le résumé dans le terminal
    print("=== Résumé du fichier GPX ===")
    print(f"Distance totale : {distance_totale:.2f} km")
    print(f"Dénivelé positif : {denivele_positif:.2f} m")
    print(f"Dénivelé négatif : {denivele_negatif:.2f} m")

    return points

def haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371.0  # Rayon de la Terre
    dlat = radians(lat2 - lat1)
    dlon = radians(lon1 - lon2)
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
            # effort = dist + (d_plus / 100) * 0.8
            # vitesse = vitesse_plat * (1 / (1 + d_plus / 500))
            # temps_h = effort / vitesse * fatigue_coeff
            
            effort = dist + (d_plus / 100)
            fatigue_coeff = 1 - (dist-distance_etape_km)/100
            diff_coeff = 1 - d_plus/2000    
            vitesse = vitesse_plat * fatigue_coeff * diff_coeff
            temps_h = effort / vitesse

            temps_total += temps_h

            # Calcul de la vitesse moyenne
            vitesse_moyenne = dist / temps_h if temps_h > 0 else 0

            etapes.append({
                "Étape": len(etapes) + 1,
                "Distance (km)": round(dist, 2),
                "D+ (m)": int(d_plus),
                "D- (m)": int(d_moins),
                "Temps (min)": int(temps_h * 60),
                "Temps (horaire)": f"{int(temps_h)}h{int((temps_h*60)%60):02d}",
"Vitesse moyenne (km/h)": round(vitesse_moyenne, 2),
                "Cumul distance (km)": round(d_tot, 2),
                "Cumul temps (horaire)": f"{int(temps_total)}h{int((temps_total*60)%60):02d}"
            })
            dist, d_plus, d_moins = 0, 0, 0

   # Ajouter une dernière étape pour la distance restante
    if dist > 0:
        effort = dist + (d_plus / 100) * 0.8
        vitesse = vitesse_plat * (1 / (1 + d_plus / 500))
        temps_h = effort / vitesse * fatigue_coeff
        temps_total += temps_h

        # Calcul de la vitesse moyenne pour la dernière étape
        vitesse_moyenne = dist / temps_h if temps_h > 0 else 0

        etapes.append({
            "Étape": len(etapes) + 1,
            "Distance (km)": round(dist, 2),
            "D+ (m)": int(d_plus),
            "D- (m)": int(d_moins),
            "Temps (min)": int(temps_h * 60),
            "Temps (horaire)": f"{int(temps_h)}h{int((temps_h*60)%60):02d}",
"Vitesse moyenne (km/h)": round(vitesse_moyenne, 2),
            "Cumul distance (km)": round(d_tot, 2),
            "Cumul temps (horaire)": f"{int(temps_total)}h{int((temps_total*60)%60):02d}"
        })

    return pd.DataFrame(etapes)

def calculer_nb_semaines(distance_totale, denivele_positif):
    # Base de 8 semaines pour une distance de 40 km et un dénivelé modéré
    base_semaines = 8
    ajout_distance = max(0, (distance_totale - 40) // 10)  # Ajouter 1 semaine par tranche de 10 km au-delà de 40 km
    ajout_difficulte = max(0, denivele_positif // 1000)  # Ajouter 1 semaine par tranche de 1000 m de D+
    return base_semaines + int(ajout_distance) + int(ajout_difficulte)

# === PLAN D’ENTRAÎNEMENT ===

def generer_plan(nb_semaines, objectif, date_course, distance_totale, denivele_positif):
    # Calculer la date de la course
    date_course_obj = datetime.strptime(date_course, "%Y-%m-%d")
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

    # Déterminer le nombre de séances par semaine en fonction de la distance
    if distance_totale > 50:
        seances_par_semaine = 6
        jours_seances = ["Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    elif distance_totale > 30:
        seances_par_semaine = 5
        jours_seances = ["Mardi", "Mercredi", "Jeudi", "Samedi", "Dimanche"]
    else:
        seances_par_semaine = 4
        jours_seances = ["Mardi", "Mercredi", "Samedi", "Dimanche"]

    plan = []

    # Fixer la phase "course" à 1 semaine
    phase_course = 1
    semaines_restantes = nb_semaines - phase_course

    # Répartir les autres phases proportionnellement
    phase_generale = max(1, int(semaines_restantes * 0.4))  # 40% des semaines restantes
    phase_specifique = max(1, int(semaines_restantes * 0.5))  # 50% des semaines restantes
    phase_affutage = max(1, semaines_restantes - (phase_generale + phase_specifique))  # Reste pour l'affûtage

    # Ajuster les sorties longues en fonction de la distance totale et du dénivelé
    sortie_longue_base = 90  # Durée de base en minutes
    ajout_duree = int(distance_totale / 10)  # Ajouter 10 min par tranche de 10 km
    ajout_difficulte = int(denivele_positif / 500)  # Ajouter 5 min par 500 m de D+
    sortie_longue_duree = sortie_longue_base + ajout_duree + ajout_difficulte

    # Nouveau tableau des types de séances par phase et jour
    types_seances = {
        "générale": {
            "Mardi": "Footing",
            "Mercredi": "PPG / Renfo",
            "Jeudi": "Vélo",
            "Vendredi": "Repos",
            "Samedi": "Sortie Longue",
            "Dimanche": "Footing"
        },
        "spécifique": {
            "Mardi": "Seuil",
            "Mercredi": "PPG / Renfo",
            "Jeudi": "VMA",
            "Vendredi": "Repos",
            "Samedi": "Sortie Longue",
            "Dimanche": "Vélo"
        },
        "affûtage": {
            "Mardi": "Footing",
            "Mercredi": "PPG / Renfo",
            "Jeudi": "Seuil",
            "Vendredi": "Repos",
            "Samedi": "Sortie Moyenne",
            "Dimanche": "Repos"
        },
        "course": {
            "Mardi": "Footing",
            "Mercredi": "VMA",
            "Jeudi": "Repos",
            "Vendredi": "Repos",
            "Samedi": "Repos",
            "Dimanche": "Course"
        }
    }

    # Contenu et conseils associés à chaque type de séance
    contenu_et_conseils = {
        "Footing": {
            "contenu": "45-60 min allure facile",
            "conseil": "Relâchement et aisance"
        },
        "PPG / Renfo": {
            "contenu": "30-40 min gainage + renfo",
            "conseil": "Posture, contrôle"
        },
        "Sortie Longue": {
            "contenu": f"{sortie_longue_duree // 60}h{sortie_longue_duree % 60:02d} trail vallonné",
            "conseil": "Hydrate-toi bien"
        },
        "Vélo": {
            "contenu": "1h tranquille ou 45 min home-trainer",
            "conseil": "Cadence souple, récup"
        },
        "Seuil": {
            "contenu": "2x10 à 3x10 min allure tempo",
            "conseil": "Tiens l’allure, respire"
        },
        "VMA": {
            "contenu": "8x45s vite / 45s récup",
            "conseil": "Explosivité, légèreté"
        },
        "Sortie Moyenne": {
            "contenu": "1h sur sentiers, allure confortable",
            "conseil": "Bonne foulée, régularité"
        },
        "Repos": {
            "contenu": "Repos complet ou 30 min marche",
            "conseil": "Bien dormir !"
        },
        "Course": {
            "contenu": "Jour J ! Donne tout 😉",
            "conseil": "Rappelle-toi pourquoi tu cours"
        }
    }

    # Calculer les séances semaine par semaine
    for semaine in range(nb_semaines):
        # Déterminer la phase en fonction de la semaine
        if semaine < phase_generale:
            phase = "générale"
        elif semaine < phase_generale + phase_specifique:
            phase = "spécifique"
        elif semaine < phase_generale + phase_specifique + phase_affutage:
            phase = "affûtage"
        else:
            phase = "course"

        jours_utilisés = 0
        for jour in jours_seances:
            if jours_utilisés >= seances_par_semaine:
                break

            # Calculer la date exacte pour le jour de la séance
            jour_index = jours_semaine.index(jour)
            date = date_course_obj - timedelta(weeks=(nb_semaines - semaine - 1), days=(5 - jour_index))

            # Récupérer le type de séance pour le jour et la phase
            type_seance = types_seances[phase].get(jour, "Repos")

            # Récupérer le contenu et le conseil associés au type de séance
            contenu = contenu_et_conseils[type_seance]["contenu"]
            conseil = contenu_et_conseils[type_seance]["conseil"]

            plan.append({
                "Semaine": semaine + 1,
                "Phase": phase,
                "Date": date.strftime("%d %B %Y").lower(),
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

def nettoyer_nom_fichier(nom):
    """
    Nettoie le nom du parcours pour l'utiliser dans les noms de fichiers.
    """
    return unicodedata.normalize('NFKD', nom).encode('ascii', 'ignore').decode('ascii').replace(' ', '_').replace('-', '_')

def export_pdf_plan(plan_df, filename="plan_entraînement_resume.pdf"):
    """
    Exporte le plan d'entraînement sous forme de tableau hebdomadaire dans un fichier PDF.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Ajouter le titre avec le nom du parcours
    titre = f"Résumé Hebdomadaire du Plan d’Entraînement\n{nom_parcours}"
    pdf.multi_cell(0, 10, txt=nettoyer_texte(titre), align='C')

    semaines = plan_df['Semaine'].unique()
    for semaine in semaines:
        phase = plan_df[plan_df['Semaine'] == semaine]['Phase'].iloc[0]
        pdf.set_font("Arial", 'B', size=12)
        pdf.cell(200, 10, nettoyer_texte(f"Semaine {semaine} - Phase: {phase}"), ln=True)
        pdf.ln(5)

        # Ajouter un tableau pour la semaine
        pdf.set_font("Arial", size=10)
        pdf.cell(30, 8, "Jour", border=1, align='C')
        pdf.cell(40, 8, "Date", border=1, align='C')
        pdf.cell(50, 8, "Type", border=1, align='C')
        pdf.cell(70, 8, "Contenu", border=1, align='C')
        pdf.ln()

        semaine_data = plan_df[plan_df['Semaine'] == semaine]
        for _, row in semaine_data.iterrows():
            pdf.cell(30, 8, nettoyer_texte(row['Jour']), border=1)
            pdf.cell(40, 8, nettoyer_texte(row['Date']), border=1)
            pdf.cell(50, 8, nettoyer_texte(row['Type']), border=1)
            pdf.cell(70, 8, nettoyer_texte(row['Contenu']), border=1)
            pdf.ln()

        pdf.ln(5)

    pdf.output(filename)
    
# Nettoyer le nom du parcours pour les fichiers
nom_fichier = nettoyer_nom_fichier(nom_parcours)

# Générer les noms des fichiers
fichier_excel = f"{nom_fichier}_planning_course.xlsx"
fichier_pdf = f"{nom_fichier}_plan_entraînement_resume.pdf"

# === EXÉCUTION ===

points = lire_trace_gpx(fichier_gpx)
df_etapes = calcul_etapes(points, distance_etape_km)

# Afficher le tableau des temps de passage dans le terminal
print("=== Tableau des Temps de Passage ===")
print(df_etapes.to_string(index=False))

# Calculer le résumé du fichier GPX
distance_totale = sum(haversine(lat1, lon1, lat2, lon2) for (_, lat1, lon1, _), (_, lat2, lon2, _) in zip(points[:-1], points[1:]))
denivele_positif = sum(max(0, ele2 - ele1) for (_, _, _, ele1), (_, _, _, ele2) in zip(points[:-1], points[1:]))
denivele_negatif = sum(max(0, ele1 - ele2) for (_, _, _, ele1), (_, _, _, ele2) in zip(points[:-1], points[1:]))

# Ajuster dynamiquement le nombre de semaines
nb_semaines = calculer_nb_semaines(distance_totale, denivele_positif)
print(f"Nombre de semaines d'entraînement ajusté : {nb_semaines}")

plan_df = generer_plan(nb_semaines, objectif, date_course, distance_totale, denivele_positif)
resume_df = ajouter_resume_hebdo(plan_df)

with pd.ExcelWriter(fichier_excel, engine="xlsxwriter") as writer:
    df_etapes.to_excel(writer, sheet_name="Temps de passage", index=False)
    plan_df.to_excel(writer, sheet_name="Plan Entrainement", index=False)
    resume_df.to_excel(writer, sheet_name="Résumé Hebdo", index=False)

# Afficher le résumé du fichier GPX à la fin
print("\n=== Résumé Final du Fichier GPX ===")
print(f"Distance totale : {distance_totale:.2f} km")
print(f"Dénivelé positif : {denivele_positif:.2f} m")
print(f"Dénivelé négatif : {denivele_negatif:.2f} m")

export_pdf_plan(plan_df, filename=fichier_pdf)
print("✅ Fichiers générés : Excel + PDF")

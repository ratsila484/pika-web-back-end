import base64
from flask import Flask, Response, request, jsonify, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import black
from PyPDF2 import PdfReader, PdfWriter
import io
import os
from datetime import datetime
from flask_cors import CORS
from flask_mysqldb import MySQL
import uuid

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'pikaAdmin'
app.config['MYSQL_PASSWORD'] = 'MonMotDePass123!'
app.config['MYSQL_DB'] = 'pika'
        
mysql = MySQL(app)

CORS(app, origins="*")
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = Response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

class PDFOverlayGenerator:
    def __init__(self):
        self.page_width = A4[0]
        self.page_height = A4[1]
        
        # Coordonnées approximatives du tableau basées sur le template
        # Ces coordonnées peuvent nécessiter un ajustement selon le PDF exact
        self.table_start_x = 1.1 * cm  # Position X de début du tableau
        self.table_start_y = 13.7 * cm  # Position Y de début du tableau (depuis le bas)
        self.row_height = 0.7 * cm     # Hauteur de chaque ligne
        self.col_widths = [12 * cm, 3 * cm, 4 * cm]  # Largeurs des colonnes
        
    def wrap_text(self, text, max_chars_per_line=60):
        """Divise le texte en lignes si nécessaire"""
        if len(text) <= max_chars_per_line:
            return [text]
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line + " " + word) <= max_chars_per_line:
                current_line += " " + word if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
            
        return lines
    
    def calculate_total_height(self, data_items):
        """Calcule la hauteur totale nécessaire pour tous les éléments"""
        total_height = 0
        for item in data_items:
            nom = item.get('nom', '')
            nom_lines = self.wrap_text(nom)
            item_height = len(nom_lines) * self.row_height
            total_height += item_height
        return total_height
    
    
    
    def create_overlay_pdf(self, data_items, numero_document="", date_document=None,textLong="",transmise=""):
        """Crée un PDF avec les données à superposer"""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Ajouter le numéro de document et la date
        if numero_document:
            c.setFont("Helvetica", 8)
            c.drawString(3.5 * cm, self.page_height - 10.4 * cm, f"{numero_document}")
        
        if date_document:
            c.setFont("Helvetica", 10)
            # Position approximative pour la date (à droite)
            c.drawRightString(18 * cm, 25.48 * cm, date_document)
        
        #ajout du texte en haut du tableau
        if transmise == '':
            c.setFont("Helvetica", 10)
            textlong = self.wrap_text(textLong,70)
            current_y = 15.4*cm
            middle_index = len(textlong) // 2
            # Dessiner chaque ligne du nom
            for i, line in enumerate(textlong):
                line_y =  current_y - (i * self.row_height)
                    
                # Colonne DESIGNATION
                if i == middle_index and len(textlong) > 1:
                        # Ligne du milieu avec le numéro
                    text_with_number = f"{line}"
                else:
                        # Autres lignes ou ligne unique
                    if len(textlong) == 1:
                        text_with_number = f"{line}"
                    else:
                        text_with_number = line
                
                c.setFont("Helvetica", 10)
                c.drawString(1.3 * cm, line_y, text_with_number)
        else : 
                c.setFont("Helvetica", 10)
                textlong = self.wrap_text(transmise, 17)  # Découpe propre du texte
                current_y = 7.8 * cm
                middle_index = len(textlong) // 2

                # Position horizontale centrée (milieu de la page)
                center_x = self.page_width / 2

                for i, line in enumerate(textlong):
                    line_y = current_y - (i * 0.4*cm)

                    if i == middle_index and len(textlong) > 1:
                        text_with_number = f"{line}"
                    else:
                        if len(textlong) == 1:
                            text_with_number = f"{line}"
                        else:
                            text_with_number = line

                    c.setFont("Helvetica-Bold", 10)
                    c.drawCentredString(center_x+6.9*cm, line_y, text_with_number)
                
        # Position de départ pour les données dans le tableau
        current_y = self.table_start_y
        total_nombres = 0
        # Parcourir les données et les placer dans le tableau
        for item in data_items:
            nom = item.get('nom', '')
            numero = item.get('numero', '000000')
            nombres = item.get('nombres', 1)
            
            # Formater le numéro à 6 chiffres
            numero_formatted = f"{int(numero):06d}"
            
            # Diviser le nom en lignes si nécessaire
            nom_lines = self.wrap_text(nom)
            
            # Calculer la position du numéro (au milieu des lignes)
            middle_index = len(nom_lines) // 2
            
            # Dessiner chaque ligne du nom
            for i, line in enumerate(nom_lines):
                line_y = current_y - (i * self.row_height)
                
                # Colonne DESIGNATION
                if i == middle_index and len(nom_lines) > 1:
                    # Ligne du milieu avec le numéro
                    text_with_number = f"{line} - IM{numero_formatted}"
                else:
                    # Autres lignes ou ligne unique
                    if len(nom_lines) == 1:
                        text_with_number = f"{line} - IM{numero_formatted}"
                    else:
                        text_with_number = line
                
                c.setFont("Helvetica", 10)
                c.drawString(self.table_start_x + 0.2 * cm, line_y, text_with_number)
                
                # Colonne NOMBRES (seulement sur la première ligne)
                if i == 0:
                    c.setFont("Helvetica", 9)
                    nombres_x = self.table_start_x + self.col_widths[0] + self.col_widths[1]/2
                    c.drawCentredString(nombres_x, line_y, str(nombres))
                    
                   
            
            # Mettre à jour la position Y pour le prochain élément
            current_y -= len(nom_lines) * self.row_height
            total_nombres += nombres
        
        # Ajouter le total à la fin
        # Position du total (en bas du tableau)
        total_y = current_y - self.row_height
        
     
        
        # Nombre total
        if transmise == '':
            c.setFont("Helvetica-Bold", 10)
            nombres_x = self.table_start_x + self.col_widths[0] + self.col_widths[1]/2
            c.drawCentredString(14.3*cm, 3.0*cm, str(total_nombres))
        else : 
            c.setFont("Helvetica-Bold", 10)
            nombres_x = self.table_start_x + self.col_widths[0] + self.col_widths[1]/2
            c.drawCentredString(14.3*cm, 3.6*cm, str(total_nombres))
        
        c.save()
        buffer.seek(0)
        return buffer
    #poursignature#####################################################################
    def ps_create_overlay_pdf(self, data_items, numero_document="", date_document=None,activite=""):
        """Crée un PDF avec les données à superposer"""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Ajouter le numéro de document et la date
        if numero_document:
            c.setFont("Helvetica-Bold", 8)
            c.drawString(15.8* cm, self.page_height - 3.87 * cm, f"{numero_document}")
        
        #activite
        c.setFont("Helvetica", 8)
        c.drawString(15 * cm, self.page_height - 2.40 * cm, f"{activite}")
        
        if date_document:
            c.setFont("Helvetica-Bold", 10)
            # Position approximative pour la date (à droite)
            c.drawRightString(18.4 * cm, 24.44 * cm, date_document)
        
        # Position de départ pour les données dans le tableau
        current_y = 21*cm
        total_nombres = 0
        # Parcourir les données et les placer dans le tableau
        for item in data_items:
            nom = item.get('nom', '')
            numero = item.get('numero', '000000')
            nombres = item.get('nombres', 1)
            
            # Formater le numéro à 6 chiffres
            numero_formatted = f"{int(numero):06d}"
            
            # Diviser le nom en lignes si nécessaire
            nom_lines = self.wrap_text(nom)
            
            # Calculer la position du numéro (au milieu des lignes)
            middle_index = len(nom_lines) // 2
            
            # Dessiner chaque ligne du nom
            for i, line in enumerate(nom_lines):
                line_y = current_y - (i * self.row_height)
                
                # Colonne DESIGNATION
                if i == middle_index and len(nom_lines) > 1:
                    # Ligne du milieu avec le numéro
                    text_with_number = f"{line} - IM{numero_formatted}"
                else:
                    # Autres lignes ou ligne unique
                    if len(nom_lines) == 1:
                        text_with_number = f"{line} - IM{numero_formatted}"
                    else:
                        text_with_number = line
                
                c.setFont("Helvetica-Bold", 11)
                c.drawString(self.table_start_x + 3.2 * cm, line_y, text_with_number)
            # Mettre à jour la position Y pour le prochain élément
            current_y -= len(nom_lines) * self.row_height
            total_nombres += nombres
        
        # Ajouter le total à la fin
        # Position du total (en bas du tableau)
        total_y = current_y - self.row_height
        # Nombre total
        c.setFont("Helvetica-Bold", 10)
        nombres_x = self.table_start_x + self.col_widths[0] + self.col_widths[1]/2
        c.drawCentredString(16.58*cm, 25.1*cm, str(total_nombres))
        
        c.save()
        buffer.seek(0)
        return buffer
    
    
    def get_sigle_from_libelle(self,libelle: str, liste: list[str], sigles: list[str]) -> str:
        try:
            index = liste.index(libelle.strip())
            return sigles[index]
        except ValueError:
            return libelle
    
    #enregistrement##################################################################
    # Listes fournies
    
    def reg_create_overlay_pdf(self, data_items, numero_document="", date_document=None):
        """Crée un PDF avec les données à superposer"""
        try:
            
            activites = [
                'Bonification',
                'Avancement',
                'Reclassement indiciaire',
                'Majoration indiciaire',
                'Nomination',
                'Reclassement par diplôme',
                'Titularisation',
                'Admission à la retraite',
                'Autorisation de sortie',
                'Départ en stage',
                'Intégration',
                'Révision de situation',
                'Renouvellement de contrat',
                'Avenant',
                'Radiation',
                'Accident de travail et Maladie Professionnel',
                'Immatriculation',
            ]

            sigleActivite = [
                'bonif',
                'avance',
                'RI',
                'MJ',
                'Nomina',
                'Reclass',
                'Titul',
                'Retraite',
                'AS',
                'Dép stg',
                'IntégR',
                'Rev situ',
                'R.contR',
                'Avenant',
                'Radiation',
                'ATMP',
                'IMM',
            ]

            ministeres = [
                'Ministère des Forces Armées',
                'Ministère des Affaires Étrangères',
                'Ministère de la Justice',
                'Ministère de la Décentralisation et de l’Aménagement du Territoire',
                'Ministère de l’Économie et des Finances',
                'Ministère de l’Intérieur',
                'Ministère de la Sécurité Publique:',
                'Ministère de l’Industrialisation et du Commerce',
                'Ministère de l’Agriculture et de l’Elevage',
                'Ministère de l’Enseignement Supérieur et de 0la Recherche Scientifique',
                'Ministère de l’Education Nationale',
                'Ministère de l’Enseignement Technique et de la Formation Professionnelle',
                'Ministère de la Santé Publique',
                'Ministère de la Population et des Solidarités',
                'Ministère du Tourisme et de l’Artisanat',
                'Ministère du Développement numérique, des Postes et des Télécommunications',
                'Ministère de l’Energie et des Hydrocarbures',
                'Ministère des Travaux Publics',
                'Ministère des Transports et de la Météorologie',
                'Ministère du Travail, de l’Emploi et de la Fonction Publique',
                'Ministère de l’Eau, de l’Assainissement et de l’Hygiène',
                'Ministère de la Pêche et de l’Economie Bleue',
                'Ministère des Mines',
                'Ministère de la Communication et de la Culture',
                'Ministère de la Jeunesse et des Sports',
                'Ministère de l’Environnement et du Développement Durable',
                'Ministère délégué en charge de la Gendarmerie Nationale',
                'Assemblée Nationale',
                'Sénat',
                'Présidence',
                'Primature',
                'Bianco',
                'Gendarmerie Nationale',
                'Imatep',
                "SENVH - Secrétariat d'Etat Charge des Nouvelles Villes et de l’Habitat",
                'Fofifa',
                'Enam',
                'Haute Cour Constitutionnelle',
                'Région Analamanga',
                'CFM, Conseil du Fampihavanana',
                'CSI - Conseil pour la Sauvegarde de l’Intégrité',
            ]

            sigleMinistere = [
                'MFA',
                'MAE',
                'MJ',
                'MDAT',
                'MEF',
                'MI',
                'MSecuP',
                'MIC',
                'MinAgri',
                'MESupReS',
                'MEN',
                'METFP',
                'MSANP',
                'MPopS',
                'MinTour',
                'MDPT',
                'MEH',
                'MTP',
                'MTM',
                'MTEFoP',
                'MEAH',
                'MPEB',
                'Mines',
                'MCC',
                'MJS',
                'MEDD',
                'Gendrm',
                'AN',
                'Sénat',
                'PRM',
                'SGG',
                'Bianco',
                'GN',
                'Imatep',
                'SENVH',
                'Fofifa',
                'Enam',
                'HCC',
                'REG',
                'CFM',
                'CSI',
            ]
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
        
            # Ajouter le numéro de document et la date
            if date_document:
                c.setFont("Helvetica", 10)
                # Position approximative pour la date (à droite)
                c.drawRightString(13.15 * cm, 27.18 * cm, str(date_document))

            
            # Définir les colonnes et leurs labels
            colonnes = [
                ("nom", 1 * cm),
                ("Matricule", 7 * cm),
                ("numeroReg", 9.4 * cm),
                ("activite", 12 * cm),
                ("ministere", 14.5 * cm),
                ("pour", 17 * cm),
                ("dispatch", 19 * cm)
            ]

            # Hauteur d'une ligne
            row_height = self.row_height
            
            # Position de départ pour les données dans le tableau
            current_y = 24 * cm
            total_nombres = 0
            startX = 0*cm
            
            # Dessiner les en-têtes
            c.setFont("Helvetica-Bold", 10)
            for label, x in colonnes:
                c.drawString(startX+x, current_y, str(label).capitalize())
            
            # Descendre pour commencer les lignes de données
            current_y -= row_height
            
            # Dessiner chaque ligne de données
            c.setFont("Helvetica", 10)
            
            # Variable pour suivre la position Y actuelle
            current_line_y = current_y
            
            # CORRECTION PRINCIPALE: Boucle correcte pour traiter chaque item
            for item_index, item in enumerate(data_items):
                try:
                    # Sécuriser l'extraction des données avec conversion en string
                    nom = str(item.get('nom', '')) if item.get('nom') is not None else ''
                    numero = str(item.get('matricule', '000000')) if item.get('matricule') is not None else '000000'
                    activite = str(item.get('activite', '')) if item.get('activite') is not None else ''
                    ministere = str(item.get('ministere', '')) if item.get('ministere') is not None else ''
                    numeroReg = str(item.get('numeroReg', '')) if item.get('numeroReg') is not None else ''
                    pour = str(item.get('pour', '')) if item.get('pour') is not None else ''
                    dispatch = str(item.get('dispatch', '')) if item.get('dispatch') is not None else ''
                    
                    # Calculer le nombre pour le total
                    nombres = item.get('nombres', 0)
                    if isinstance(nombres, (int, float)):
                        total_nombres += nombres
                    elif isinstance(nombres, str) and nombres.isdigit():
                        total_nombres += int(nombres)

                    # Formater le numéro avec gestion d'erreur
                    try:
                        if numero.isdigit():
                            numero_formatted = f"{int(numero):06d}"
                        else:
                            numero_formatted = numero[:6].zfill(6)  # Fallback si ce n'est pas un nombre
                    except (ValueError, TypeError):
                        numero_formatted = "000000"

                    # Gérer noms multilignes avec une largeur maximale
                    nom_lines = self.wrap_text_with_width(nom, 2.8*cm) if nom else ['']
                    
                    # Calculer l'espace nécessaire pour cette entrée
                    lines_needed = max(1, len(nom_lines))
                    space_needed = lines_needed * (row_height * 0.4)  # Espacement réduit entre les lignes du nom
                    
                    # Vérifier si on a assez de place sur la page
                    if current_line_y - space_needed < 2 * cm:  # Marge de sécurité en bas de page
                        c.showPage()  # Nouvelle page
                        current_line_y = 21 * cm
                        
                        # Redessiner les en-têtes sur la nouvelle page
                        c.setFont("Helvetica-Bold", 10)
                        for label, x in colonnes:
                            c.drawString(startX+x, current_line_y + row_height, str(label).capitalize())
                        c.setFont("Helvetica", 10)

                    # Position de base pour cette ligne (première ligne du nom)
                    base_y = current_line_y
                    
                    sigle_activite = self.get_sigle_from_libelle(activite, activites, sigleActivite)
                    sigle_ministere = self.get_sigle_from_libelle(ministere, ministeres, sigleMinistere)
                    # Dessiner les données de base (toujours sur la première ligne)
                    c.drawString(colonnes[1][1], base_y, numero_formatted)
                    c.drawString(colonnes[2][1], base_y, numeroReg)
                    c.drawString(colonnes[3][1], base_y, sigle_activite)
                    c.drawString(colonnes[4][1], base_y, sigle_ministere)
                    c.drawString(colonnes[5][1], base_y, pour)
                    c.drawString(colonnes[6][1], base_y, dispatch)

                    # Dessiner le nom multiligne
                    for line_index, nom_line in enumerate(nom_lines):
                        if nom_line.strip():  # Ne dessiner que si la ligne n'est pas vide
                            nom_y = base_y - (line_index * row_height * 0.5)  # Espacement réduit
                            c.drawString(startX + colonnes[0][1], nom_y, str(nom_line.strip()))

                    # Mettre à jour la position Y pour la prochaine entrée
                    current_line_y -= max(row_height, space_needed)

                except Exception as e:
                    print(f"Erreur lors du traitement de l'item {item_index}: {e}")
                    print(f"Item data: {item}")
                    # Continuer avec un espacement normal même en cas d'erreur
                    current_line_y -= row_height
                    continue

            c.save()
            buffer.seek(0)
            return buffer
            
            
        except Exception as e:
            print(f"Erreur générale dans reg_create_overlay_pdf: {e}")
            print(f"Type de data_items: {type(data_items)}")
            if data_items:
                print(f"Premier item: {data_items[0] if len(data_items) > 0 else 'Aucun item'}")
            raise
    
    
    
    
    def wrap_text_with_width(self, text, max_width=5.5*cm, font_name="Helvetica", font_size=10):
        """
        Découpe le texte en lignes selon une largeur maximale
        """
        if not text:
            return ['']
        
        # Estimation approximative: 1 cm ≈ 28 caractères pour Helvetica 10pt
        chars_per_cm = 10
        max_chars = int(max_width * chars_per_cm / cm)
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            # Vérifier si ajouter ce mot dépasse la largeur
            test_line = current_line + (" " if current_line else "") + word
            
            if len(test_line) <= max_chars:
                current_line = test_line
            else:
                # Si la ligne courante n'est pas vide, la sauvegarder
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Si le mot seul est trop long, le tronquer
                    if len(word) > max_chars:
                        lines.append(word[:max_chars-3] + "...")
                        current_line = ""
                    else:
                        current_line = word
        
        # Ajouter la dernière ligne si elle n'est pas vide
        if current_line:
            lines.append(current_line)
        
        return lines if lines else ['']
    
    #be###################################################################""
    def overlay_on_existing_pdf(self, existing_pdf_path, data_items, numero_document="", date_document=None,textLong="",transmise=""):
        """Superpose les données sur un PDF existant"""
        try:
            
            # Lire le PDF existant
            with open(existing_pdf_path, 'rb') as file:
                existing_pdf = PdfReader(file)
                
                # Créer le PDF overlay avec les données
                overlay_buffer = self.create_overlay_pdf(data_items, numero_document, date_document,textLong,transmise)
                overlay_pdf = PdfReader(overlay_buffer)
                
                # Créer le PDF final
                output_pdf = PdfWriter()
                
                # Superposer sur chaque page (normalement une seule page)
                for page_num in range(len(existing_pdf.pages)):
                    page = existing_pdf.pages[page_num]
                    
                    # Superposer les données si on a une page overlay correspondante
                    if page_num < len(overlay_pdf.pages):
                        overlay_page = overlay_pdf.pages[page_num]
                        page.merge_page(overlay_page)
                    
                    output_pdf.add_page(page)
                
                # Sauvegarder dans un buffer
                output_buffer = io.BytesIO()
                output_pdf.write(output_buffer)
                output_buffer.seek(0)
                
                return output_buffer
                
        except Exception as e:
            raise Exception(f"Erreur lors de la superposition PDF: {str(e)}")
        
#signature###############################################################
    def ps_overlay_on_existing_pdf(self, existing_pdf_path, data_items, numero_document="", date_document=None,activite=""):
        """Superpose les données sur un PDF existant"""
        try:
            
            # Lire le PDF existant
            with open(existing_pdf_path, 'rb') as file:
                existing_pdf = PdfReader(file)
                    
                    # Créer le PDF overlay avec les données
                overlay_buffer = self.ps_create_overlay_pdf(data_items, numero_document, date_document,activite)
                overlay_pdf = PdfReader(overlay_buffer)
                    
                    # Créer le PDF final
                output_pdf = PdfWriter()
                    
                    # Superposer sur chaque page (normalement une seule page)
                for page_num in range(len(existing_pdf.pages)):
                    page = existing_pdf.pages[page_num]
                        
                        # Superposer les données si on a une page overlay correspondante
                    if page_num < len(overlay_pdf.pages):
                        overlay_page = overlay_pdf.pages[page_num]
                        page.merge_page(overlay_page)
                        
                        output_pdf.add_page(page)
                    
                    # Sauvegarder dans un buffer
                    output_buffer = io.BytesIO()
                    output_pdf.write(output_buffer)
                    output_buffer.seek(0)
                    
                    return output_buffer
                    
        except Exception as e:
            raise Exception(f"Erreur lors de la superposition PDF: {str(e)}")
    
    
    
    
    #enregistrement################################################################""
    def reg_overlay_on_existing_pdf(self, existing_pdf_path, data_items, numero_document="", date_document=None):
        """Superpose les données sur un PDF existant"""
        try:
            
            # Lire le PDF existant
            with open(existing_pdf_path, 'rb') as file:
                existing_pdf = PdfReader(file)
                    
                    # Créer le PDF overlay avec les données
                overlay_buffer = self.reg_create_overlay_pdf(data_items, numero_document, date_document)
                overlay_pdf = PdfReader(overlay_buffer)
                    
                    # Créer le PDF final
                output_pdf = PdfWriter()
                    
                    # Superposer sur chaque page (normalement une seule page)
                for page_num in range(len(existing_pdf.pages)):
                    page = existing_pdf.pages[page_num]
                        
                        # Superposer les données si on a une page overlay correspondante
                    if page_num < len(overlay_pdf.pages):
                        overlay_page = overlay_pdf.pages[page_num]
                        page.merge_page(overlay_page)
                        
                        output_pdf.add_page(page)
                    
                    # Sauvegarder dans un buffer
                    output_buffer = io.BytesIO()
                    output_pdf.write(output_buffer)
                    output_buffer.seek(0)
                    
                    return output_buffer
                    
        except Exception as e:
            raise Exception(f"Erreur lors de la superposition PDF: {str(e)}")
        
def chercher_pdf_correspondant(template):
    dossier_templates = 'templates/be'
    pdf_path = f"{template}.pdf"  # par exemple: "CF ANE.pdf"
    
    fichiers = os.listdir(dossier_templates)
    fichiers_pdf = [f for f in fichiers if f.lower().endswith('.pdf')]

    print(f"Fichier recherché: {pdf_path}")
    print("Fichiers trouvés dans le dossier templates:")

    for f in fichiers_pdf:
        print(f" - {f}")
        if f == os.path.basename(pdf_path):
            print(">>> Correspondance trouvée !")
            return os.path.join(dossier_templates, f)

    print(">>> Aucune correspondance trouvée.")
    return None

def generer_text_long(activite, noms, statut="contractuel"):
    cpt = len(noms)

    textLong1 = f"Projet d’arrêté portant {activite}"

    if statut == "contractuel":
        if cpt == 1:
            textLong2 = "d’un agent contractuel"
        else:
            textLong2 = "des agents contractuels"
    else:  # fonctionnaire
        if cpt == 1:
            textLong2 = "d’un fonctionnaire"
        else:
            textLong2 = "des fonctionnaires"

    return f"{textLong1} {textLong2}"

def getstatut(template):
    if template == "CF ANE" or template == "Fin effectif" or template == "MAE":
        return "contractuel"
    else:
        return "fonctionnare"


# Instance du générateur
generator = PDFOverlayGenerator()

@app.route('/')
def index():
    return '''
    <h1>Générateur de Bordereau d'Envoi - Superposition PDF</h1>
    <p>Cette application superpose des données sur un PDF existant.</p>
    <p>Assurez-vous d'avoir le fichier 'CF.pdf' dans le même dossier que l'application.</p>
    
    <h2>Endpoints disponibles:</h2>
    <ul>
        <li><strong>POST /overlay_pdf</strong> - Superpose des données personnalisées</li>
        <li><strong>GET /test_overlay</strong> - Test avec données d'exemple</li>
    </ul>
    
    <h2>Exemple de données JSON pour POST /overlay_pdf:</h2>
    <pre>
{
    "numero_document": "001",
    "date_document": "15/12/2024",
    "items": [
        {
            "nom": "ANDRIAMPITIANVA Tsiory Famonjena Sylvain Sylvestre",
            "numero": "123456",
            "nombres": 5,
        },
        {
            "nom": "Rapport mensuel",
            "numero": "789012",
            "nombres": 2,
        }
    ]
}
    </pre>
    '''
#be
@app.route('/overlay_pdf', methods=['POST'])
def overlay_pdf():
    try:
        data = request.get_json()
        if data :
            print(data)
             
        numero_doc = data.get('numero_document', '')
        date_doc = data.get('date_document', '')
        template = data.get('template','')
        activite = data.get('activite','')
        transmise = data.get('transmise')
        
        print("template = ", template)
        print("activite = ", activite)
        
        
        # Vérifier que le fichier PDF existe
        
        chemin_pdf = chercher_pdf_correspondant(template)
        if chemin_pdf:
            pdf_path = f"templates/be/{template}.pdf"
            if not os.path.exists(pdf_path):
                return jsonify({'error': 'Fichier CF.pdf non trouvé. Veuillez le placer dans le dossier de l\'application.'}), 404
        if not data or 'consorts' not in data:
            return jsonify({'error': 'Données manquantes. Veuillez fournir un tableau "items".'}), 400
        pdf_path = pdf_path
        
        items = data['consorts']
        # Validation des items
        for item in items:
            if 'nom' not in item:
                return jsonify({'error': 'Chaque item doit avoir un "nom".'}), 400
            if 'matricule' not in item:
                item['matricule'] = '000000'
            if 'nombres' not in item:
                item['matricule'] = 1
        textLong = generer_text_long(activite, items,getstatut(template))
                
        # Générer le texte à insérer
        # Superposition sur le PDF existant
        result_buffer = generator.overlay_on_existing_pdf(pdf_path, items, numero_doc, date_doc,textLong,transmise)
        
        return send_file(
            result_buffer,
            as_attachment=True,
            download_name=f'bordereau_rempli_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la superposition: {str(e)}'}), 500

#pour signature
@app.route('/ps_overlay_pdf',methods=['POST'])
def ps_pdf():
    try:
        data = request.get_json()
        if data :
            print(data)
             
        numero_doc = data.get('numero_document', '') #parapheur
        date_doc = data.get('date_document', '') #date
        activite = data.get('activite','') #division
        
        # Vérifier que le fichier PDF existe
        template = "signature"
        #chemin_pdf = chercher_pdf_correspondant(template)
        pdf_path = f"templates/ps/model.pdf"
        if not os.path.exists(pdf_path):
            return jsonify({'error': 'model.pdf non trouvé. Veuillez le placer dans le dossier de l\'application.'}), 404
        if not data or 'consorts' not in data:
            return jsonify({'error': 'Données manquantes. Veuillez fournir un tableau "items".'}), 400
        pdf_path = pdf_path
        
        items = data['consorts']
        # Validation des items
        for item in items:
            if 'nom' not in item:
                return jsonify({'error': 'Chaque item doit avoir un "nom".'}), 400
            if 'matricule' not in item:
                item['matricule'] = '000000'
            if 'nombres' not in item:
                item['matricule'] = 1
                
        # Générer le texte à insérer
        # Superposition sur le PDF existant
        result_buffer = generator.ps_overlay_on_existing_pdf(pdf_path, items, numero_doc, date_doc,activite)
        
        return send_file(
            result_buffer,
            as_attachment=True,
            download_name=f'bordereau_rempli_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la superposition: {str(e)}'}), 500

#enregistrement###################################################################
@app.route('/reg_overlay_pdf',methods=['POST'])
def reg_pdf():
    try:
        data = request.get_json()
        if data :
            print(data)
             
        numero_doc = data.get('numero_document', '') #parapheur
        date_doc = data.get('date_document', '') #date
        
        #chemin_pdf = chercher_pdf_correspondant(template)
        pdf_path = f"templates/enreg/modelEnregistrement.pdf"
        if not os.path.exists(pdf_path):
            return jsonify({'error': 'model.pdf non trouvé. Veuillez le placer dans le dossier de l\'application.'}), 404
        if not data or 'consorts' not in data:
            return jsonify({'error': 'Données manquantes. Veuillez fournir un tableau "items".'}), 400
        pdf_path = pdf_path
        
        items = data['consorts']
        # Validation des items
        for item in items:
            if 'nom' not in item:
                return jsonify({'error': 'Chaque item doit avoir un "nom".'}), 400
            if 'matricule' not in item:
                item['matricule'] = '000000'
                
        # Générer le texte à insérer
        # Superposition sur le PDF existant
        result_buffer = generator.reg_overlay_on_existing_pdf(pdf_path, items, numero_doc, date_doc)
        
        return send_file(
            result_buffer,
            as_attachment=True,
            download_name=f'bordereau_rempli_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la superposition: {str(e)}'}), 500

@app.route('/test_overlay', methods=['GET'])
def test_overlay():
    """Endpoint de test avec des données d'exemple"""
    
    
    # Vérifier que le fichier PDF existe
    pdf_path = 'templates/be/CF ANE.pdf'
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'Fichier CF.pdf non trouvé. Veuillez le placer dans le dossier de l\'application.'}), 404
    
    test_data = [
        {
            "nom": "ANDRIAMPITIANVA Tsiory Famonjena Sylvain Sylvestre",
            "numero": "123456",
            "nombres": 5,
        },
        {
            "nom": "Rapport mensuel d'activités",
            "numero": "789012",
            "nombres": 2,
        },
        {
            "nom": "Factures diverses",
            "numero": "345678",
            "nombres": 10,
        }
    ]
    
    try:
        result_buffer = generator.overlay_on_existing_pdf(
            pdf_path, 
            test_data,
            "0010",
            "15/12/2024"
        )
        
        return send_file(
            result_buffer,
            as_attachment=True,
            download_name='test_bordereau_rempli.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la superposition: {str(e)}'}), 500

@app.route('/upload_template', methods=['POST'])
def upload_template():
    """Permet d'uploader un nouveau template PDF"""
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    if file and file.filename.lower().endswith('.pdf'):
        file.save('CF.pdf')
        return jsonify({'message': 'Template PDF uploadé avec succès'})
    
    return jsonify({'error': 'Veuillez fournir un fichier PDF valide'}), 400

#sauver dans la bdd PS
@app.route('/save_in_database', methods=['POST'])
def save_ps():
    data = request.get_json();
    if data:
        print("data received")
    
    numero_doc = data.get('numero_document','')
    activite = data.get('activite','')
    date_document = data.get('date_document','')
    items = data['consorts']

    #generation d'un id unique
    
    chemin = ""
    pdf_base64 = data.get('pdf_base64')
    if pdf_base64:
        # Retirer l'entête "data:application/pdf;base64,"
        header, encoded = pdf_base64.split(',', 1)
        pdf_bytes = base64.b64decode(encoded)
        save_dir = 'documents/ps'
        os.makedirs(save_dir, exist_ok=True)
        pdfName = "ps"+numero_doc+"_"+".pdf"
        chemin = save_dir+"/"+pdfName
        with open(os.path.join(save_dir, pdfName), "wb") as f:
            f.write(pdf_bytes)
        
    for item in items:
        unique_id = str(uuid.uuid4())
        nom = item.get('nom','')
        matricule = item.get('matricule','').replace(' ','')[:6]
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO documents (id,numero,nom,matricule,activite,chemin) VALUES (%s, %s,%s,%s,%s,%s)" , (unique_id,numero_doc,nom,matricule,activite,chemin))
    
    
    
    mysql.connection.commit()
    cur.close()
    
    
    return jsonify({'message':True})

#sauver dans la bdd BE
@app.route('/save_in_database_be', methods=['POST'])
def save_be():
    data = request.get_json();
    if data:
        print("data received")
    
    numero_doc = data.get('numero_document','')
    activite = data.get('activite','')
    date_document = data.get('date_document','')
    items = data['consorts']
    template = data.get('template')
    #generation d'un id unique
    
    chemin = ""
    pdf_base64 = data.get('pdf_base64')
    if pdf_base64:
        # Retirer l'entête "data:application/pdf;base64,"
        header, encoded = pdf_base64.split(',', 1)
        pdf_bytes = base64.b64decode(encoded)
        save_dir = 'documents/be'
        os.makedirs(save_dir, exist_ok=True)
        pdfName = "ps"+numero_doc+"_"+".pdf"
        chemin = save_dir+"/"+pdfName
        with open(os.path.join(save_dir, pdfName), "wb") as f:
            f.write(pdf_bytes)
        
    for item in items:
        unique_id = str(uuid.uuid4())
        nom = item.get('nom','')
        matricule = item.get('matricule','').replace(' ','')[:6]
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO BE (id,numero,chemin,activite,nom,matricule,model) VALUES (%s, %s,%s,%s,%s,%s,%s)" , (unique_id,numero_doc,chemin,activite,nom,matricule,template))
    
    
    
    mysql.connection.commit()
    cur.close()
    
    
    return jsonify({'message':True})

#save database enregistrement
@app.route('/save_in_database_reg', methods=['POST'])
def save_reg():
    data = request.get_json();
    if data:
        print("data received")
    
    date_document = data.get('date_document','').replace('/', '_')
    items = data['consorts']
    #generation d'un id unique
    
    chemin = ""
    pdf_base64 = data.get('pdf_base64')
    if pdf_base64:
        # Retirer l'entête "data:application/pdf;base64,"
        header, encoded = pdf_base64.split(',', 1)
        pdf_bytes = base64.b64decode(encoded)
        save_dir = 'documents/reg'
        os.makedirs(save_dir, exist_ok=True)
        pdfName = "enreg_"+date_document+"_"+".pdf"
        chemin = save_dir+"/"+pdfName
        with open(os.path.join(save_dir, pdfName), "wb") as f:
            f.write(pdf_bytes)
        
    for item in items:
        unique_id = str(uuid.uuid4())
        nom = item.get('nom','')
        matricule = item.get('matricule','').replace(' ','')[:6]
        ministere = item.get('ministere','')
        activite = item.get('activite','')
        numeroReg = item.get('numeroReg','')
        dispatch = item.get('dispatch','')
        pour = item.get('pour','')
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO enregistrement (id,nom,matricule,ministere,activite,numeroReg,dispatch,pour,chemin) VALUES (%s, %s,%s,%s,%s,%s,%s,%s,%s)" , (unique_id,nom,matricule,ministere,activite,numeroReg,dispatch,pour,chemin))
    
    
    
    mysql.connection.commit()
    cur.close()
    
    
    return jsonify({'message':True})


#recuperer tous les pour signature
@app.route('/get_ps',methods=['GET'])
def getPs():
    
    result = ""
    cur= mysql.connection.cursor()
    cur.execute("SELECT * FROM documents")
    result = cur.fetchall()
    cur.close()
    
    return jsonify({'message':True,'data':result})


#recuperer tous les fichier be
@app.route('/get_be',methods=['GET'])
def getBe():
    
    result = ""
    cur= mysql.connection.cursor()
    cur.execute("SELECT * FROM BE")
    result = cur.fetchall()
    cur.close()
    
    return jsonify({'message':True,'data':result})

#enregistrement 
@app.route('/get_reg',methods=['GET'])
def getReg():
    
    result = ""
    cur= mysql.connection.cursor()
    cur.execute("SELECT * FROM enregistrement")
    result = cur.fetchall()
    cur.close()
    
    return jsonify({'message':True,'data':result})


#recuperer un fichier Ps
@app.route('/getPs_pdf',methods=['POST'])
def getPsPdf():
    data = request.get_json()
    id = data.get('id','')
    print(id)
    #id = "909a903e-1925-4f84-b330-e5e93e05c36d"
    if not id:
        return jsonify({'error':'ID manquant'}), 400
    
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT chemin FROM documents WHERE id = %s", (id,))
    chemin = cur.fetchone()
    cur.close()
    
    pdf_path = chemin[0]
    
    if os.path.exists(pdf_path):
        return send_file(pdf_path,as_attachment=True,download_name=f"{id}.pdf")
    else : 
        return jsonify({'error':'fichier non trouver'}),404
    
#recuperer un fichier Ps
@app.route('/getBe_pdf',methods=['POST'])
def getBePdf():
    data = request.get_json()
    id = data.get('id','')
    #print(id)
    #id = "a6c2ea45-18ef-4e48-ba77-9f362c04b8fd"
    if not id:
        return jsonify({'error':'ID manquant'}), 400
    
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT chemin FROM BE WHERE id = %s", (id,))
    chemin = cur.fetchone()
    cur.close()
    
    pdf_path = chemin[0]
    
    if os.path.exists(pdf_path):
        return send_file(pdf_path,as_attachment=True,download_name=f"{id}.pdf")
    else : 
        return jsonify({'error':'fichier non trouver'}),404
    
#recuperer un fichier Reg
@app.route('/getReg_pdf',methods=['POST'])
def getRegPdf():
    data = request.get_json()
    id = data.get('id','')
    #print(id)
    #id = "a6c2ea45-18ef-4e48-ba77-9f362c04b8fd"
    if not id:
        return jsonify({'error':'ID manquant'}), 400
    
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT chemin FROM enregistrement WHERE id = %s", (id,))
    chemin = cur.fetchone()
    cur.close()
    
    pdf_path = chemin[0]
    
    if os.path.exists(pdf_path):
        return send_file(pdf_path,as_attachment=True,download_name=f"{id}.pdf")
    else : 
        return jsonify({'error':'fichier non trouver'}),404
        
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    

import re
from datetime import datetime
from typing import Dict, Optional
import pytesseract
from PIL import Image

class PassportExtractor:
    """
    Classe pour extraire et valider les données d'un passeport
    """
    
    def __init__(self, image_path: str):
        """
        Initialise l'extracteur avec le chemin de l'image du passeport
        
        Args:
            image_path: Chemin vers l'image du passeport
        """
        self.image_path = image_path
        self.extracted_data = {}
        
    def extract_text_from_image(self) -> str:
        """
        Extrait le texte de l'image du passeport en utilisant OCR
        
        Returns:
            Texte extrait de l'image
        """
        try:
            image = Image.open(self.image_path)
            # Extraction du texte avec Tesseract
            text = pytesseract.image_to_string(image, lang='fra+eng')
            return text
        except Exception as e:
            raise Exception(f"Erreur lors de l'extraction du texte: {str(e)}")
    
    def extract_mrz(self, text: str) -> Optional[Dict]:
        """
        Extrait les données de la Machine Readable Zone (MRZ) du passeport
        La MRZ est la zone avec les caractères << >> en bas du passeport
        
        Args:
            text: Texte extrait du passeport
            
        Returns:
            Dictionnaire contenant les données extraites
        """
        # Pattern pour MRZ de passeport (2 lignes de 44 caractères)
        mrz_pattern = r'P<[A-Z]{3}[A-Z<]+\n[A-Z0-9<]{44}'
        mrz_match = re.search(mrz_pattern, text.replace(' ', ''))
        
        if mrz_match:
            mrz_lines = mrz_match.group().split('\n')
            return self._parse_mrz(mrz_lines)
        return None
    
    def _parse_mrz(self, mrz_lines: list) -> Dict:
        """
        Parse les lignes MRZ du passeport
        
        Args:
            mrz_lines: Liste des lignes MRZ
            
        Returns:
            Dictionnaire avec les données parsées
        """
        data = {}
        
        # Première ligne: Type, Code pays, Nom
        line1 = mrz_lines[0]
        data['type'] = line1[0]  # P pour passeport
        data['pays_code'] = line1[2:5]
        
        # Extraction du nom (séparé par <<)
        nom_partie = line1[5:].split('<<')
        if len(nom_partie) >= 2:
            data['nom'] = nom_partie[0].replace('<', ' ').strip()
            data['prenoms'] = nom_partie[1].replace('<', ' ').strip()
        
        # Deuxième ligne: Numéro, Nationalité, Date naissance, Sexe, Date expiration
        line2 = mrz_lines[1]
        data['numero_passeport'] = line2[0:9].replace('<', '').strip()
        data['nationalite'] = line2[10:13]
        data['date_naissance'] = self._parse_date(line2[13:19])
        data['sexe'] = line2[20]
        data['date_expiration'] = self._parse_date(line2[21:27])
        
        return data
    
    def _parse_date(self, date_str: str) -> str:
        """
        Convertit une date MRZ (YYMMDD) en format lisible
        
        Args:
            date_str: Date au format YYMMDD
            
        Returns:
            Date au format YYYY-MM-DD
        """
        try:
            year = int(date_str[0:2])
            # Si l'année est < 50, on considère 20XX, sinon 19XX
            year = 2000 + year if year < 50 else 1900 + year
            month = date_str[2:4]
            day = date_str[4:6]
            return f"{year}-{month}-{day}"
        except:
            return date_str
    
    def extract_general_info(self, text: str) -> Dict:
        """
        Extrait les informations générales du passeport (en complément de la MRZ)
        
        Args:
            text: Texte extrait du passeport
            
        Returns:
            Dictionnaire avec les informations extraites
        """
        data = {}
        
        # Patterns pour différents champs
        patterns = {
            'numero_passeport': r'(?:Passport\s*No\.?|N°\s*de\s*passeport|Passeport\s*N°)\s*[:\s]*([A-Z0-9]+)',
            'nom': r'(?:Surname|Nom)\s*[:\s]*([A-Z\s]+)',
            'prenoms': r'(?:Given names|Prénoms)\s*[:\s]*([A-Z\s]+)',
            'date_naissance': r'(?:Date of birth|Date de naissance)\s*[:\s]*(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            'lieu_naissance': r'(?:Place of birth|Lieu de naissance)\s*[:\s]*([A-Z\s]+)',
            'date_emission': r'(?:Date of issue|Date de délivrance)\s*[:\s]*(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            'date_expiration': r'(?:Date of expiry|Date d\'expiration)\s*[:\s]*(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            'autorite': r'(?:Authority|Autorité)\s*[:\s]*([A-Z\s]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()
        
        return data
    
    def validate_passport(self, expiry_date: str) -> Dict:
        """
        Vérifie la validité du passeport en comparant la date d'expiration à aujourd'hui
        
        Args:
            expiry_date: Date d'expiration au format YYYY-MM-DD ou DD/MM/YYYY
            
        Returns:
            Dictionnaire avec le statut de validité et des informations
        """
        try:
            # Conversion de la date d'expiration
            if '-' in expiry_date:
                expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
            else:
                expiry = datetime.strptime(expiry_date, '%d/%m/%Y')
            
            today = datetime.now()
            
            # Calcul de la différence
            diff = expiry - today
            days_remaining = diff.days
            
            result = {
                'date_expiration': expiry.strftime('%d/%m/%Y'),
                'date_verification': today.strftime('%d/%m/%Y'),
                'est_valide': days_remaining > 0,
                'jours_restants': days_remaining if days_remaining > 0 else 0,
                'expire': days_remaining <= 0
            }
            
            # Messages
            if days_remaining > 180:
                result['message'] = f"Passeport valide. Expire dans {days_remaining} jours."
                result['niveau_alerte'] = 'vert'
            elif days_remaining > 0:
                result['message'] = f"Attention: Le passeport expire bientôt ({days_remaining} jours)."
                result['niveau_alerte'] = 'orange'
            else:
                result['message'] = f"Passeport expiré depuis {abs(days_remaining)} jours."
                result['niveau_alerte'] = 'rouge'
            
            return result
            
        except ValueError as e:
            return {
                'erreur': f"Format de date invalide: {str(e)}",
                'est_valide': False
            }
    
    def process(self) -> Dict:
        """
        Traite l'image du passeport et retourne toutes les données extraites
        avec validation
        
        Returns:
            Dictionnaire complet avec les données et la validation
        """
        result = {
            'success': False,
            'donnees': {},
            'validation': {}
        }
        
        try:
            # Extraction du texte
            text = self.extract_text_from_image()
            
            # Tentative d'extraction MRZ (plus fiable)
            mrz_data = self.extract_mrz(text)
            if mrz_data:
                result['donnees'] = mrz_data
                result['methode'] = 'MRZ'
            else:
                # Si pas de MRZ, extraction générale
                result['donnees'] = self.extract_general_info(text)
                result['methode'] = 'OCR général'
            
            # Validation si date d'expiration trouvée
            if 'date_expiration' in result['donnees']:
                result['validation'] = self.validate_passport(
                    result['donnees']['date_expiration']
                )
            
            result['success'] = True
            result['texte_brut'] = text  # Pour debug
            
        except Exception as e:
            result['erreur'] = str(e)
        
        return result


def main():
    """
    Exemple d'utilisation
    """
    # Chemin vers l'image du passeport
    image_path = "/chemin/vers/votre/passport.jpg"
    
    # Créer l'extracteur
    extractor = PassportExtractor(image_path)
    
    # Traiter le passeport
    resultat = extractor.process()
    
    if resultat['success']:
        print("=== DONNÉES DU PASSEPORT ===")
        for key, value in resultat['donnees'].items():
            print(f"{key}: {value}")
        
        print("\n=== VALIDATION ===")
        validation = resultat['validation']
        if validation:
            print(f"Statut: {validation['message']}")
            print(f"Niveau d'alerte: {validation['niveau_alerte']}")
            print(f"Date d'expiration: {validation['date_expiration']}")
            if validation['est_valide']:
                print(f"Jours restants: {validation['jours_restants']}")
    else:
        print(f"Erreur: {resultat.get('erreur', 'Erreur inconnue')}")


if __name__ == "__main__":
    main()
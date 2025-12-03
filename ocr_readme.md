# Guide d'installation et d'utilisation - Extracteur de passeport

## 1. Installation des dépendances

### Installation de Tesseract OCR

#### Sur Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-fra  # Pour le français
sudo apt-get install tesseract-ocr-eng  # Pour l'anglais
```

#### Sur macOS:
```bash
brew install tesseract
brew install tesseract-lang  # Pour les langues supplémentaires
```

#### Sur Windows:
Téléchargez l'installeur depuis: https://github.com/UB-Mannheim/tesseract/wiki
Ajoutez le chemin d'installation à votre PATH

### Installation des packages Python
```bash
pip install -r requirements.txt
```

## 2. Utilisation du script standalone

```python
from passport_extractor import PassportExtractor

# Créer l'extracteur
extractor = PassportExtractor("/chemin/vers/passport.jpg")

# Extraire et valider
resultat = extractor.process()

if resultat['success']:
    print("Données extraites:", resultat['donnees'])
    print("Validation:", resultat['validation'])
else:
    print("Erreur:", resultat['erreur'])
```

## 3. Intégration avec Django

### Étape 1: Ajouter le modèle dans votre app

Copiez le modèle `PassportData` de `django_integration.py` dans votre `models.py`

### Étape 2: Créer les migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Étape 3: Ajouter les vues

Copiez les vues de `django_integration.py` dans votre `views.py`

### Étape 4: Configurer les URLs

Dans votre `urls.py`:
```python
from django.urls import path
from . import views

urlpatterns = [
    path('api/passport/extract/', views.extract_passport_data, name='extract_passport'),
    path('api/passport/validate/', views.validate_passport_expiry, name='validate_passport'),
]
```

### Étape 5: Configurer les médias

Dans `settings.py`:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## 4. Exemples d'utilisation de l'API

### Extraction complète avec image

```bash
curl -X POST http://localhost:8000/api/passport/extract/ \
  -F "passport_image=@/chemin/vers/passport.jpg"
```

Réponse:
```json
{
  "success": true,
  "donnees": {
    "numero_passeport": "12AB34567",
    "nom": "DUPONT",
    "prenoms": "JEAN PIERRE",
    "date_naissance": "1985-03-15",
    "sexe": "M",
    "nationalite": "FRA",
    "pays_code": "FRA",
    "date_expiration": "2028-12-31"
  },
  "validation": {
    "date_expiration": "31/12/2028",
    "date_verification": "29/11/2025",
    "est_valide": true,
    "jours_restants": 1128,
    "expire": false,
    "message": "Passeport valide. Expire dans 1128 jours.",
    "niveau_alerte": "vert"
  },
  "methode": "MRZ"
}
```

### Validation de date uniquement

```bash
curl -X POST http://localhost:8000/api/passport/validate/ \
  -H "Content-Type: application/json" \
  -d '{"expiry_date": "2025-06-30"}'
```

Réponse:
```json
{
  "success": true,
  "validation": {
    "date_expiration": "30/06/2025",
    "date_verification": "29/11/2025",
    "est_valide": false,
    "jours_restants": 0,
    "expire": true,
    "message": "Passeport expiré depuis 152 jours.",
    "niveau_alerte": "rouge"
  }
}
```

## 5. Frontend avec Vue.js

```vue
<template>
  <div class="passport-extractor">
    <h2>Extraction de passeport</h2>
    
    <div class="upload-zone">
      <input 
        type="file" 
        @change="handleFileUpload" 
        accept="image/*"
        ref="fileInput"
      />
      <button @click="$refs.fileInput.click()">
        Sélectionner un passeport
      </button>
    </div>
    
    <div v-if="loading" class="loading">
      Extraction en cours...
    </div>
    
    <div v-if="result" class="result">
      <h3>Résultats</h3>
      
      <div class="passport-data">
        <div class="field">
          <label>Numéro:</label>
          <span>{{ result.donnees.numero_passeport }}</span>
        </div>
        <div class="field">
          <label>Nom:</label>
          <span>{{ result.donnees.nom }}</span>
        </div>
        <div class="field">
          <label>Prénoms:</label>
          <span>{{ result.donnees.prenoms }}</span>
        </div>
        <div class="field">
          <label>Date de naissance:</label>
          <span>{{ result.donnees.date_naissance }}</span>
        </div>
        <div class="field">
          <label>Date d'expiration:</label>
          <span>{{ result.donnees.date_expiration }}</span>
        </div>
      </div>
      
      <div 
        class="validation-alert" 
        :class="result.validation.niveau_alerte"
      >
        <strong>{{ result.validation.message }}</strong>
        <p v-if="result.validation.est_valide">
          Jours restants: {{ result.validation.jours_restants }}
        </p>
      </div>
    </div>
    
    <div v-if="error" class="error">
      {{ error }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'PassportExtractor',
  data() {
    return {
      loading: false,
      result: null,
      error: null
    }
  },
  methods: {
    async handleFileUpload(event) {
      const file = event.target.files[0]
      if (!file) return
      
      this.loading = true
      this.error = null
      this.result = null
      
      const formData = new FormData()
      formData.append('passport_image', file)
      
      try {
        const response = await fetch('/api/passport/extract/', {
          method: 'POST',
          body: formData
        })
        
        const data = await response.json()
        
        if (data.success) {
          this.result = data
        } else {
          this.error = data.error || 'Erreur lors de l\'extraction'
        }
      } catch (err) {
        this.error = 'Erreur de connexion au serveur'
        console.error(err)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.passport-extractor {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.upload-zone {
  margin: 20px 0;
}

.upload-zone input[type="file"] {
  display: none;
}

.upload-zone button {
  padding: 10px 20px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.passport-data {
  margin: 20px 0;
}

.field {
  display: flex;
  margin: 10px 0;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 4px;
}

.field label {
  font-weight: bold;
  width: 150px;
}

.validation-alert {
  padding: 15px;
  border-radius: 4px;
  margin: 20px 0;
}

.validation-alert.vert {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.validation-alert.orange {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeeba;
}

.validation-alert.rouge {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.loading, .error {
  padding: 15px;
  margin: 20px 0;
  border-radius: 4px;
}

.loading {
  background: #e3f2fd;
  color: #0d47a1;
}

.error {
  background: #ffebee;
  color: #c62828;
}
</style>
```

## 6. Améliorer la précision de l'OCR

### Prétraitement d'image

Ajoutez ces fonctions pour améliorer la qualité avant OCR:

```python
import cv2
import numpy as np

def preprocess_image(image_path):
    """
    Prétraite l'image pour améliorer l'OCR
    """
    # Charger l'image
    img = cv2.imread(image_path)
    
    # Convertir en niveaux de gris
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Réduire le bruit
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # Augmenter le contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    # Binarisation
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Sauvegarder l'image prétraitée
    preprocessed_path = image_path.replace('.jpg', '_preprocessed.jpg')
    cv2.imwrite(preprocessed_path, binary)
    
    return preprocessed_path
```

## 7. Tests

### Test unitaire

```python
import unittest
from passport_extractor import PassportExtractor

class TestPassportExtractor(unittest.TestCase):
    
    def test_validate_valid_passport(self):
        extractor = PassportExtractor("")
        result = extractor.validate_passport("2028-12-31")
        self.assertTrue(result['est_valide'])
        self.assertEqual(result['niveau_alerte'], 'vert')
    
    def test_validate_expired_passport(self):
        extractor = PassportExtractor("")
        result = extractor.validate_passport("2020-01-01")
        self.assertFalse(result['est_valide'])
        self.assertEqual(result['niveau_alerte'], 'rouge')
    
    def test_validate_expiring_soon(self):
        from datetime import datetime, timedelta
        extractor = PassportExtractor("")
        future_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
        result = extractor.validate_passport(future_date)
        self.assertTrue(result['est_valide'])
        self.assertEqual(result['niveau_alerte'], 'orange')

if __name__ == '__main__':
    unittest.main()
```

## 8. Considérations de sécurité

1. **Stockage sécurisé**: Ne stockez jamais les images de passeport en clair
2. **Chiffrement**: Chiffrez les données sensibles dans la base de données
3. **Validation**: Validez toujours les fichiers uploadés
4. **Permissions**: Limitez l'accès aux données de passeport
5. **Logs**: N'enregistrez pas les données sensibles dans les logs
6. **RGPD**: Respectez les règlements sur la protection des données

## 9. Limitations

- La qualité de l'extraction dépend de la qualité de l'image
- La MRZ doit être lisible pour une extraction optimale
- Tesseract peut avoir des difficultés avec certaines polices
- Les passeports très anciens peuvent ne pas avoir de MRZ

## 10. Dépannage

### "Tesseract not found"
Vérifiez que Tesseract est installé et dans le PATH

### Mauvaise extraction
- Améliorez la qualité de l'image
- Assurez-vous que le passeport est bien éclairé
- Évitez les reflets sur l'image
- Utilisez le prétraitement d'image
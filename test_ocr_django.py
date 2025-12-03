# views.py - Exemple d'intégration Django

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
import os
from passport_extractor import PassportExtractor


@csrf_exempt
def extract_passport_data(request):
    """
    API endpoint pour extraire les données d'un passeport
    
    Method: POST
    Content-Type: multipart/form-data
    Body: passport_image (file)
    
    Returns: JSON avec les données extraites et la validation
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Méthode non autorisée. Utilisez POST.'
        }, status=405)
    
    if 'passport_image' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': 'Aucune image de passeport fournie.'
        }, status=400)
    
    try:
        # Récupérer le fichier uploadé
        passport_file = request.FILES['passport_image']
        
        # Sauvegarder temporairement le fichier
        file_name = f'temp_passport_{request.user.id if request.user.is_authenticated else "anonymous"}.jpg'
        file_path = default_storage.save(file_name, ContentFile(passport_file.read()))
        full_path = default_storage.path(file_path)
        
        # Extraire les données
        extractor = PassportExtractor(full_path)
        result = extractor.process()
        
        # Nettoyer le fichier temporaire
        if os.path.exists(full_path):
            os.remove(full_path)
        
        # Retourner les résultats
        return JsonResponse(result, status=200 if result['success'] else 400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors du traitement: {str(e)}'
        }, status=500)


@csrf_exempt
def validate_passport_expiry(request):
    """
    API endpoint pour valider uniquement la date d'expiration d'un passeport
    
    Method: POST
    Content-Type: application/json
    Body: {"expiry_date": "YYYY-MM-DD" ou "DD/MM/YYYY"}
    
    Returns: JSON avec le statut de validité
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Méthode non autorisée. Utilisez POST.'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        expiry_date = data.get('expiry_date')
        
        if not expiry_date:
            return JsonResponse({
                'success': False,
                'error': 'Date d\'expiration manquante.'
            }, status=400)
        
        # Valider la date
        extractor = PassportExtractor("")  # Pas besoin d'image pour cette validation
        validation = extractor.validate_passport(expiry_date)
        
        return JsonResponse({
            'success': True,
            'validation': validation
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON invalide.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/passport/extract/', views.extract_passport_data, name='extract_passport'),
    path('api/passport/validate/', views.validate_passport_expiry, name='validate_passport'),
]


# models.py - Modèle pour stocker les données du passeport
from django.db import models
from django.contrib.auth.models import User

class PassportData(models.Model):
    """
    Modèle pour stocker les données extraites d'un passeport
    """
    SEXE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
    
    NIVEAU_ALERTE_CHOICES = [
        ('vert', 'Valide'),
        ('orange', 'Expire bientôt'),
        ('rouge', 'Expiré'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passports')
    
    # Informations du passeport
    numero_passeport = models.CharField(max_length=20, unique=True)
    nom = models.CharField(max_length=100)
    prenoms = models.CharField(max_length=200)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=200, blank=True, null=True)
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES)
    nationalite = models.CharField(max_length=3)
    pays_code = models.CharField(max_length=3)
    
    # Dates importantes
    date_emission = models.DateField(null=True, blank=True)
    date_expiration = models.DateField()
    
    # Autorité émettrice
    autorite = models.CharField(max_length=200, blank=True, null=True)
    
    # Statut de validité
    est_valide = models.BooleanField(default=True)
    niveau_alerte = models.CharField(max_length=10, choices=NIVEAU_ALERTE_CHOICES, default='vert')
    jours_restants = models.IntegerField(default=0)
    
    # Métadonnées
    image_passeport = models.ImageField(upload_to='passports/', null=True, blank=True)
    methode_extraction = models.CharField(max_length=20, default='OCR')
    date_extraction = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_mise_a_jour']
        verbose_name = 'Passeport'
        verbose_name_plural = 'Passeports'
    
    def __str__(self):
        return f"{self.numero_passeport} - {self.nom} {self.prenoms}"
    
    def update_validation_status(self):
        """
        Met à jour le statut de validité du passeport
        """
        from datetime import datetime
        
        today = datetime.now().date()
        diff = (self.date_expiration - today).days
        
        self.jours_restants = diff if diff > 0 else 0
        self.est_valide = diff > 0
        
        if diff > 180:
            self.niveau_alerte = 'vert'
        elif diff > 0:
            self.niveau_alerte = 'orange'
        else:
            self.niveau_alerte = 'rouge'
        
        self.save()


# serializers.py (si vous utilisez Django REST Framework)
from rest_framework import serializers
from .models import PassportData

class PassportDataSerializer(serializers.ModelSerializer):
    message_validite = serializers.SerializerMethodField()
    
    class Meta:
        model = PassportData
        fields = '__all__'
        read_only_fields = ['user', 'est_valide', 'niveau_alerte', 'jours_restants', 
                           'date_extraction', 'date_mise_a_jour']
    
    def get_message_validite(self, obj):
        if obj.jours_restants > 180:
            return f"Passeport valide. Expire dans {obj.jours_restants} jours."
        elif obj.est_valide:
            return f"Attention: Le passeport expire bientôt ({obj.jours_restants} jours)."
        else:
            return "Passeport expiré."
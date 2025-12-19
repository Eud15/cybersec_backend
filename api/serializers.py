# api/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from decimal import Decimal
from .models import (
    TypeActif, Architecture, Actif, AttributSecurite, Menace, AttributMenace,
     Technique, MesureDeControle, 
    ImplementationMesure, LogActivite, CategorieActif, TypeActif, MenaceMesure
)




# ============================================================================
# SERIALIZERS POUR CATÉGORIES ET TYPES D'ACTIFS (NOUVEAUX)
# ============================================================================

class TypeActifSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    categorie_code = serializers.CharField(source='categorie.code', read_only=True)
    actifs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TypeActif
        fields = [
            'id', 'categorie', 'categorie_nom', 'categorie_code',
            'nom', 'code', 'description', 'actifs_count', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_actifs_count(self, obj):
        return obj.actifs.count()

class TypeActifCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeActif
        fields = ['categorie', 'nom', 'code', 'description']
    
    def validate_code(self, value):
        """Valide que le code est en majuscules et sans espaces"""
        if not value.replace('-', '').replace('_', '').isalnum():
            raise serializers.ValidationError(
                "Le code ne doit contenir que des lettres, chiffres, tirets et underscores"
            )
        return value.upper()
    
    def validate(self, data):
        """Valide l'unicité du nom dans la catégorie"""
        categorie = data.get('categorie')
        nom = data.get('nom')
        
        instance_id = self.instance.id if self.instance else None
        
        if TypeActif.objects.filter(
            categorie=categorie, 
            nom=nom
        ).exclude(id=instance_id).exists():
            raise serializers.ValidationError({
                'nom': f'Un type avec le nom "{nom}" existe déjà dans cette catégorie'
            })
        
        return data

class TypeActifListSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    categorie_code = serializers.CharField(source='categorie.code', read_only=True)
    actifs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TypeActif
        fields = [
            'id', 'categorie_nom', 'categorie_code', 'nom', 'code', 
            'actifs_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_actifs_count(self, obj):
        return obj.actifs.count()

class CategorieActifSerializer(serializers.ModelSerializer):
    types_actifs = TypeActifListSerializer(many=True, read_only=True)
    types_count = serializers.SerializerMethodField()
    actifs_total_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CategorieActif
        fields = [
            'id', 'nom', 'code', 'description', 
            'types_actifs', 'types_count', 'actifs_total_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_types_count(self, obj):
        return obj.types_actifs.count()
    
    def get_actifs_total_count(self, obj):
        """Compte tous les actifs de tous les types de cette catégorie"""
        return sum(type_actif.actifs.count() for type_actif in obj.types_actifs.all())

class CategorieActifCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorieActif
        fields = ['nom', 'code', 'description']
    
    def validate_code(self, value):
        """Valide que le code est en majuscules et sans espaces"""
        if not value.replace('-', '').replace('_', '').isalnum():
            raise serializers.ValidationError(
                "Le code ne doit contenir que des lettres, chiffres, tirets et underscores"
            )
        return value.upper()

class CategorieActifListSerializer(serializers.ModelSerializer):
    types_count = serializers.SerializerMethodField()
    actifs_total_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CategorieActif
        fields = [
            'id', 'nom', 'code', 'description',
            'types_count', 'actifs_total_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_types_count(self, obj):
        return obj.types_actifs.count()
    
    def get_actifs_total_count(self, obj):
        return sum(type_actif.actifs.count() for type_actif in obj.types_actifs.all())
    

# ============================================================================
# SERIALIZERS DE BASE
# ============================================================================

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']
        read_only_fields = ['id']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username



# ============================================================================
# SERIALIZERS POUR MESURES DE CONTROLE ET IMPLEMENTATIONS
# ============================================================================

class ImplementationMesureSerializer(serializers.ModelSerializer):
    mesure_nom = serializers.CharField(source='mesure_controle.nom', read_only=True)
    mesure_efficacite = serializers.DecimalField(source='mesure_controle.efficacite', max_digits=5, decimal_places=2, read_only=True)
    responsable_nom = serializers.CharField(source='responsable.get_full_name', read_only=True)
    risque_residuel_calculated = serializers.ReadOnlyField(source='risque_residuel')
    
    class Meta:
        model = ImplementationMesure
        fields = [
            'id', 'attribut_menace', 'mesure_controle', 'mesure_nom', 'mesure_efficacite',
            'statut', 'date_debut_prevue', 'date_fin_prevue', 'date_implementation',
            'responsable', 'responsable_nom', 'equipe', 'pourcentage_avancement',
            'commentaires', 'obstacles', 'risque_residuel_calculated', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class MesureDeControleSerializer(serializers.ModelSerializer):
    technique_code = serializers.CharField(source='technique.technique_code', read_only=True)
    technique_nom = serializers.CharField(source='technique.nom', read_only=True)
    technique_famille = serializers.CharField(source='technique.famille', read_only=True)
    cout_total_3_ans_calculated = serializers.ReadOnlyField(source='cout_total_3_ans')
    implementations = ImplementationMesureSerializer(many=True, read_only=True)
    implementations_count = serializers.SerializerMethodField()
    menaces_traitees_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MesureDeControle
        fields = [
            'id', 'mesure_code', 'nom', 'description', 'nature_mesure',
            'cout_mise_en_oeuvre', 'cout_maintenance_annuel', 'efficacite',
            'duree_implementation', 'ressources_necessaires',
            'technique', 'technique_code', 'technique_nom', 'technique_famille',
            'cout_total_3_ans_calculated', 'implementations', 'implementations_count',
            'menaces_traitees_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_implementations_count(self, obj):
        return obj.implementations.count()
    
    def get_menaces_traitees_count(self, obj):
        return obj.menaces_traitees.count()


class MesureDeControleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MesureDeControle
        fields = [
            'technique', 'mesure_code', 'nom', 'description', 'nature_mesure',
            'cout_mise_en_oeuvre', 'cout_maintenance_annuel', 'efficacite',
            'duree_implementation', 'ressources_necessaires'
        ]
    
    def validate_efficacite(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("L'efficacité doit être entre 0 et 100.")
        return value
    
    def validate_mesure_code(self, value):
        """Valide le format du code mesure"""
        if value:
            import re
            if not re.match(r'^[A-Z]{1,4}-\d{3,4}$', value):
                raise serializers.ValidationError(
                    "Le code mesure doit suivre le format: XX-NNN ou XXXX-NNNN (ex: M-001, MEAS-0001)"
                )
            return value.upper()
        return value

class MenaceMesureSerializer(serializers.ModelSerializer):
    mesure_nom = serializers.CharField(source='mesure_controle.nom', read_only=True)
    mesure_code = serializers.CharField(source='mesure_controle.mesure_code', read_only=True)
    mesure_efficacite = serializers.DecimalField(source='mesure_controle.efficacite', max_digits=5, decimal_places=2, read_only=True)
    technique_nom = serializers.CharField(source='mesure_controle.technique.nom', read_only=True)
    technique_code = serializers.CharField(source='mesure_controle.technique.technique_code', read_only=True)
    mesure_detail = MesureDeControleSerializer(source='mesure_controle', read_only=True)
    
    class Meta:
        model = MenaceMesure
        fields = [
            'id', 'menace', 'mesure_controle', 'mesure_nom', 'mesure_code',
            'mesure_efficacite', 'technique_nom', 'technique_code',
            'efficacite', 'statut_conformite', 'commentaires',
            'mesure_detail', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class MenaceMesureCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenaceMesure
        fields = ['menace', 'mesure_controle', 'efficacite', 'statut_conformite', 'commentaires']
# ============================================================================
# SERIALIZERS POUR TECHNIQUES
# ============================================================================

class TechniqueSerializer(serializers.ModelSerializer):
    mesures_controle = MesureDeControleSerializer(many=True, read_only=True)
    mesures_count = serializers.SerializerMethodField()
    cout_moyen_mesures = serializers.SerializerMethodField()
    menaces_traitees_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Technique
        fields = [
            'id', 'technique_code', 'nom', 'description', 'type_technique', 
            'complexite', 'famille', 'priorite',
            'mesures_controle', 'mesures_count', 'cout_moyen_mesures',
            'menaces_traitees_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_mesures_count(self, obj):
        return obj.mesures_controle.count()
    
    def get_cout_moyen_mesures(self, obj):
        mesures = obj.mesures_controle.all()
        if not mesures:
            return 0
        total_cout = sum(float(mesure.cout_mise_en_oeuvre) for mesure in mesures)
        return round(total_cout / len(mesures), 2)
    
    def get_menaces_traitees_count(self, obj):
        """Compte le nombre de menaces traitées par cette technique via ses mesures"""
        menaces_ids = set()
        for mesure in obj.mesures_controle.all():
            menaces_ids.update(mesure.menaces_traitees.values_list('menace_id', flat=True))
        return len(menaces_ids)


class TechniqueCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technique
        fields = ['technique_code', 'nom', 'description', 'type_technique', 'complexite', 'famille', 'priorite']
    
    def validate_technique_code(self, value):
        """Valide le format du code technique"""
        if not value:
            raise serializers.ValidationError("Le code technique est requis.")
        
        import re
        if not re.match(r'^[A-Z]{1,4}-\d{3,4}$', value):
            raise serializers.ValidationError(
                "Le code technique doit suivre le format: XX-NNN ou XXXX-NNNN (ex: T-001, TECH-0001)"
            )
        
        return value.upper()


class TechniqueListSerializer(serializers.ModelSerializer):
    mesures_count = serializers.SerializerMethodField()
    menaces_traitees_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Technique
        fields = [
            'id', 'technique_code', 'nom', 'type_technique', 'complexite',
            'famille', 'priorite', 'mesures_count', 'menaces_traitees_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_mesures_count(self, obj):
        return obj.mesures_controle.count()
    
    def get_menaces_traitees_count(self, obj):
        menaces_ids = set()
        for mesure in obj.mesures_controle.all():
            menaces_ids.update(mesure.menaces_traitees.values_list('menace_id', flat=True))
        return len(menaces_ids)






# ============================================================================
# SERIALIZERS POUR MENACES
# ============================================================================

class MenaceSerializer(serializers.ModelSerializer):
    mesures_controle = MenaceMesureSerializer(many=True, read_only=True)
    attributs_impactes_count = serializers.SerializerMethodField()
    
    # Informations hiérarchiques
    architecture_id = serializers.SerializerMethodField()
    architecture_nom = serializers.SerializerMethodField()
    actif_id = serializers.SerializerMethodField()
    actif_nom = serializers.SerializerMethodField()
    attribut_securite_id = serializers.SerializerMethodField()
    attribut_type = serializers.SerializerMethodField()
    
    # Métriques consolidées
    total_mesures = serializers.SerializerMethodField()
    total_techniques = serializers.SerializerMethodField()
    cout_total_protection = serializers.SerializerMethodField()
    taux_conformite = serializers.SerializerMethodField()
    
    class Meta:
        model = Menace
        fields = [
            'id', 'nom', 'description', 'type_menace', 'severite',
            
            # Hiérarchie parent
            'architecture_id', 'architecture_nom',
            'actif_id', 'actif_nom', 
            'attribut_securite_id', 'attribut_type',
            
            # Relations et métriques
            'mesures_controle', 'attributs_impactes_count',
            'total_mesures', 'total_techniques',
            'cout_total_protection', 'taux_conformite',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def _get_attribut_principal(self, obj):
        """Méthode helper pour récupérer l'attribut principal"""
        attr_menace = obj.attributs_impactes.select_related(
            'attribut_securite__actif__architecture'
        ).first()
        
        return attr_menace.attribut_securite if attr_menace else None
    
    def get_architecture_id(self, obj):
        attribut = self._get_attribut_principal(obj)
        return str(attribut.actif.architecture.id) if attribut else None
    
    def get_architecture_nom(self, obj):
        attribut = self._get_attribut_principal(obj)
        return attribut.actif.architecture.nom if attribut else None
    
    def get_actif_id(self, obj):
        attribut = self._get_attribut_principal(obj)
        return str(attribut.actif.id) if attribut else None
    
    def get_actif_nom(self, obj):
        attribut = self._get_attribut_principal(obj)
        return attribut.actif.nom if attribut else None
    
    def get_attribut_securite_id(self, obj):
        attribut = self._get_attribut_principal(obj)
        return str(attribut.id) if attribut else None
    
    def get_attribut_type(self, obj):
        attribut = self._get_attribut_principal(obj)
        return attribut.type_attribut if attribut else None
    
    def get_attributs_impactes_count(self, obj):
        return obj.attributs_impactes.count()
    
    def get_total_mesures(self, obj):
        return obj.mesures_controle.count()
    
    def get_total_techniques(self, obj):
        """Compte les techniques uniques via les mesures"""
        techniques_ids = set()
        for menace_mesure in obj.mesures_controle.select_related('mesure_controle__technique').all():
            techniques_ids.add(menace_mesure.mesure_controle.technique.id)
        return len(techniques_ids)
    
    def get_cout_total_protection(self, obj):
        total = 0
        for menace_mesure in obj.mesures_controle.select_related('mesure_controle').all():
            total += menace_mesure.mesure_controle.cout_total_3_ans
        return round(total, 2)
    
    def get_taux_conformite(self, obj):
        mesures = obj.mesures_controle.all()
        if not mesures:
            return 0
        conformes = mesures.filter(statut_conformite='CONFORME').count()
        return round((conformes / mesures.count()) * 100, 2)


class MenaceListSerializer(serializers.ModelSerializer):
    attributs_impactes_count = serializers.SerializerMethodField()
    mesures_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Menace
        fields = [
            'id', 'nom', 'description', 'type_menace', 'severite',
            'attributs_impactes_count', 'mesures_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_attributs_impactes_count(self, obj):
        return obj.attributs_impactes.count()
    
    def get_mesures_count(self, obj):
        return obj.mesures_controle.count()

# Serializer pour la création/modification avec gestion du contexte principal
class MenaceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menace
        fields = [
            'nom', 'description', 'type_menace', 'severite', 
            'attribut_securite_principal'
        ]
    
    def validate_attribut_securite_principal(self, value):
        """Validation de l'attribut de sécurité principal"""
        if value:
            # Vérifier que l'attribut existe et est actif
            if not AttributSecurite.objects.filter(id=value.id).exists():
                raise serializers.ValidationError(
                    "L'attribut de sécurité spécifié n'existe pas."
                )
        return value




# ============================================================================
# SERIALIZERS POUR ATTRIBUT-MENACE
# ============================================================================

class AttributMenaceSerializer(serializers.ModelSerializer):
    menace_detail = MenaceSerializer(source='menace', read_only=True)
    menace_nom = serializers.CharField(source='menace.nom', read_only=True)
    menace_severite = serializers.CharField(source='menace.severite', read_only=True)
    attribut_nom = serializers.CharField(source='attribut_securite.actif.nom', read_only=True)
    attribut_type = serializers.CharField(source='attribut_securite.type_attribut', read_only=True)
    niveau_risque_calculated = serializers.ReadOnlyField(source='niveau_risque')
    risque_financier_calculated = serializers.ReadOnlyField(source='risque_financier')
    
    # Solutions recommandées
    solutions_recommandees = serializers.SerializerMethodField()
    implementations = ImplementationMesureSerializer(many=True, read_only=True)
    
    class Meta:
        model = AttributMenace
        fields = [
            'id', 'attribut_securite', 'menace', 'menace_nom', 'menace_severite',
            'attribut_nom', 'attribut_type', 'probabilite', 'impact', 'cout_impact',
            'niveau_risque_calculated', 'risque_financier_calculated',
            'menace_detail', 'solutions_recommandees', 'implementations',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_solutions_recommandees(self, obj):
        """Retourne les 3 meilleures solutions (ratio efficacité/coût)"""
        solutions = []
        
        # Parcourir directement les mesures de contrôle liées à la menace
        for menace_mesure in obj.menace.mesures_controle.select_related('mesure_controle__technique').all():
            mesure = menace_mesure.mesure_controle
            
            if mesure.efficacite and mesure.cout_total_3_ans > 0:
                ratio_efficacite_cout = float(mesure.efficacite) / mesure.cout_total_3_ans
                solutions.append({
                    'mesure_id': mesure.id,
                    'mesure_nom': mesure.nom,
                    'mesure_code': mesure.mesure_code,
                    'technique_nom': mesure.technique.nom,
                    'technique_code': mesure.technique.technique_code,
                    'efficacite': float(mesure.efficacite),
                    'cout_3_ans': mesure.cout_total_3_ans,
                    'ratio_efficacite_cout': round(ratio_efficacite_cout, 4),
                    'duree_implementation': mesure.duree_implementation,
                    'nature_mesure': mesure.nature_mesure,
                    'statut_conformite': menace_mesure.statut_conformite
                })
        
        # Trier par ratio efficacité/coût décroissant et prendre les 3 premiers
        solutions.sort(key=lambda x: x['ratio_efficacite_cout'], reverse=True)
        return solutions[:3]


class AttributMenaceCreateSerializer(serializers.ModelSerializer):
    # Champs de l'association
    probabilite = serializers.DecimalField(max_digits=5, decimal_places=2, required=True)
    
    # Champs optionnels pour modifier la menace
    nom = serializers.CharField(max_length=200, required=False, write_only=True)
    description = serializers.CharField(required=False, write_only=True, allow_blank=True)
    type_menace = serializers.CharField(max_length=50, required=False, write_only=True)
    
    class Meta:
        model = AttributMenace
        fields = ['attribut_securite', 'menace', 'probabilite', 'impact', 'cout_impact', 
                 'nom', 'description', 'type_menace']
        
    def update(self, instance, validated_data):
        # Séparer les données de l'association et de la menace
        association_data = {k: v for k, v in validated_data.items() 
                          if k not in ['nom', 'description', 'type_menace']}
        menace_data = {k: v for k, v in validated_data.items() 
                      if k in ['nom', 'description', 'type_menace']}
        
        # Mettre à jour l'association
        for attr, value in association_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Mettre à jour la menace si nécessaire
        if menace_data:
            menace = instance.menace
            for attr, value in menace_data.items():
                if hasattr(menace, attr):
                    setattr(menace, attr, value)
            menace.save()
        
        return instance

# ============================================================================
# SERIALIZERS POUR ATTRIBUTS DE SECURITE
# ============================================================================

class AttributSecuriteSerializer(serializers.ModelSerializer):
    actif_nom = serializers.CharField(source='actif.nom', read_only=True)
    actif_code = serializers.CharField(source='actif.actif_code', read_only=True)
    menaces = serializers.SerializerMethodField()
    
    class Meta:
        model = AttributSecurite
        fields = '__all__'
    
    def get_menaces(self, obj):
        """
        Retourne les menaces avec leurs mesures de contrôle
        
        IMPORTANT: obj.menaces.all() retourne des AttributMenace (relation M2M through)
        Il faut donc accéder à attr_menace.menace pour avoir l'objet Menace
        """
        menaces_data = []
        
        # ✅ Itérer sur les AttributMenace
        for attr_menace in obj.menaces.all():
            # ✅ Extraire l'objet Menace
            menace = attr_menace.menace
            
            # Récupérer les mesures de contrôle via MenaceMesure
            mesures_controle = []
            for menace_mesure in menace.mesures_controle.select_related('mesure_controle__technique').all():
                mesure = menace_mesure.mesure_controle
                mesures_controle.append({
                    'id': str(mesure.id),
                    'mesure_code': mesure.mesure_code,
                    'nom': mesure.nom,
                    'technique_code': mesure.technique.technique_code,
                    'technique_nom': mesure.technique.nom,
                    'efficacite': float(mesure.efficacite),
                    'nature_mesure': mesure.nature_mesure
                })
            
            menaces_data.append({
                # Données de la menace
                'id': str(menace.id),
                'nom': menace.nom,
                'severite': menace.severite,
                'type_menace': menace.type_menace,
                'description': menace.description,
                
                # Données de l'association AttributMenace
                'probabilite': float(attr_menace.probabilite),
                'impact': float(attr_menace.impact),
                'cout_impact': float(attr_menace.cout_impact),
                'niveau_risque': attr_menace.niveau_risque,
                'risque_financier': attr_menace.risque_financier,
                
                # Mesures de contrôle disponibles
                'mesures_count': len(mesures_controle),
                'mesures_controle': mesures_controle[:5]  # Limiter à 5 pour performance
            })
        
        return menaces_data

class AttributSecuriteListSerializer(serializers.ModelSerializer):
    actif_nom = serializers.CharField(source='actif.nom', read_only=True)
    menaces_count = serializers.SerializerMethodField()
    risque_financier_attribut = serializers.ReadOnlyField()
    ratio_risque_cout = serializers.ReadOnlyField()
    niveau_alerte = serializers.ReadOnlyField()
    
    class Meta:
        model = AttributSecurite
        fields = [
            'id', 'actif', 'actif_nom', 'type_attribut', 'cout_compromission', 'priorite',
            'risque_financier_attribut', 'ratio_risque_cout', 'niveau_alerte',
            'menaces_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_menaces_count(self, obj):
        return obj.menaces.count()

class AttributSecuriteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributSecurite
        fields = ['actif', 'type_attribut', 'cout_compromission', 'priorite']
    
    def validate_cout_compromission(self, value):
        if value < 0:
            raise serializers.ValidationError("Le coût de compromission doit être positif.")
        return value

# ============================================================================
# SERIALIZERS POUR ACTIFS
# ============================================================================

class ActifSerializer(serializers.ModelSerializer):
    type_actif_nom = serializers.CharField(source='type_actif.nom', read_only=True)
    architecture_nom = serializers.CharField(source='architecture.nom', read_only=True)
    proprietaire_nom = serializers.CharField(source='proprietaire.get_full_name', read_only=True)
    attributs_securite = AttributSecuriteListSerializer(many=True, read_only=True)
    attributs_count = serializers.SerializerMethodField()
    risque_financier_total = serializers.SerializerMethodField()
    
    class Meta:
        model = Actif
        fields = [
            'id', 'nom', 'description', 'cout', 'criticite',
            'type_actif', 'type_actif_nom', 'architecture', 'architecture_nom',
            'proprietaire', 'proprietaire_nom', 'attributs_securite',
            'attributs_count', 'risque_financier_total', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_attributs_count(self, obj):
        return obj.attributs_securite.count()
    
    def get_risque_financier_total(self, obj):
        total = 0
        for attr_secu in obj.attributs_securite.all():
            total += attr_secu.risque_financier_attribut
        return round(total, 2)

class ActifListSerializer(serializers.ModelSerializer):
    type_actif_nom = serializers.CharField(source='type_actif.nom', read_only=True)
    proprietaire_nom = serializers.CharField(source='proprietaire.get_full_name', read_only=True)
    attributs_count = serializers.SerializerMethodField()
    risque_financier_total = serializers.SerializerMethodField()
    
    class Meta:
        model = Actif
        fields = [
            'id', 'nom', 'description', 'cout', 'criticite',
            'type_actif', 'type_actif_nom', 'architecture', 'proprietaire', 'proprietaire_nom',
            'attributs_count', 'risque_financier_total', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_attributs_count(self, obj):
        return obj.attributs_securite.count()
    
    def get_risque_financier_total(self, obj):
        total = 0
        for attr_secu in obj.attributs_securite.all():
            total += attr_secu.risque_financier_attribut
        return round(total, 2)

class ActifCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actif
        fields = ['nom', 'description', 'cout', 'criticite', 'type_actif', 'architecture', 'proprietaire']
    
    def validate_cout(self, value):
        if value < 0:
            raise serializers.ValidationError("Le coût doit être positif.")
        return value

# ============================================================================
# SERIALIZERS POUR ARCHITECTURES
# ============================================================================

class ArchitectureSerializer(serializers.ModelSerializer):
    actifs = ActifListSerializer(many=True, read_only=True)
    actifs_count = serializers.SerializerMethodField()
    risque_financier_total = serializers.SerializerMethodField()
    risque_depasse_tolerance = serializers.SerializerMethodField()
    pourcentage_tolerance_utilise = serializers.SerializerMethodField()
    risque_par_criticite = serializers.SerializerMethodField()
    
    class Meta:
        model = Architecture
        fields = [
            'id', 'nom', 'description', 'risque_tolere', 'actifs_count',
            'risque_financier_total', 'risque_depasse_tolerance',
            'pourcentage_tolerance_utilise', 'risque_par_criticite',
            'actifs', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_actifs_count(self, obj):
        return obj.actifs.count()
    
    def get_risque_financier_total(self, obj):
        return obj.risque_financier_total
    
    def get_risque_depasse_tolerance(self, obj):
        return obj.risque_depasse_tolerance
    
    def get_pourcentage_tolerance_utilise(self, obj):
        return round(obj.pourcentage_tolerance_utilise, 2)
    
    def get_risque_par_criticite(self, obj):
        """Analyse des risques financiers par niveau de criticité"""
        risques_par_criticite = {}
        
        for actif in obj.actifs.all():
            criticite = actif.criticite
            if criticite not in risques_par_criticite:
                risques_par_criticite[criticite] = 0
            
            for attr_secu in actif.attributs_securite.all():
                risques_par_criticite[criticite] += attr_secu.risque_financier_attribut
        
        return {k: round(v, 2) for k, v in risques_par_criticite.items()}

class ArchitectureListSerializer(serializers.ModelSerializer):
    actifs_count = serializers.SerializerMethodField()
    risque_financier_total = serializers.SerializerMethodField()
    risque_depasse_tolerance = serializers.SerializerMethodField()
    pourcentage_tolerance_utilise = serializers.SerializerMethodField()
    
    class Meta:
        model = Architecture
        fields = [
            'id', 'nom', 'description', 'risque_tolere', 'actifs_count',
            'risque_financier_total', 'risque_depasse_tolerance',
            'pourcentage_tolerance_utilise', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_actifs_count(self, obj):
        return obj.actifs.count()
    
    def get_risque_financier_total(self, obj):
        return obj.risque_financier_total
    
    def get_risque_depasse_tolerance(self, obj):
        return obj.risque_depasse_tolerance
    
    def get_pourcentage_tolerance_utilise(self, obj):
        return round(obj.pourcentage_tolerance_utilise, 2)

class ArchitectureCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Architecture
        fields = ['nom', 'description', 'risque_tolere']
    
    def validate_risque_tolere(self, value):
        if value < 0:
            raise serializers.ValidationError("Le risque toléré doit être positif.")
        return value

# ============================================================================
# SERIALIZERS POUR LOGS ET DASHBOARD
# ============================================================================

class LogActiviteSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='utilisateur.username', read_only=True)
    
    class Meta:
        model = LogActivite
        fields = [
            'id', 'utilisateur', 'utilisateur_nom', 'action', 'objet_type',
            'objet_id', 'details', 'adresse_ip', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques du dashboard"""
    total_architectures = serializers.IntegerField()
    total_actifs = serializers.IntegerField()
    total_attributs = serializers.IntegerField()
    total_menaces = serializers.IntegerField()
    
    total_techniques = serializers.IntegerField()
    total_mesures = serializers.IntegerField()
    
    # Risques financiers
    risque_financier_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    architectures_hors_tolerance = serializers.IntegerField()
    budget_risque_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Conformité
   
    implementations_en_cours = serializers.IntegerField()
    
    # Répartitions
    actifs_par_criticite = serializers.DictField()
    menaces_par_severite = serializers.DictField()
    implementations_par_statut = serializers.DictField()
    risque_par_architecture = serializers.DictField()

class MenaceSimpleCreateSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    probabilite = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)
    
    def validate_nom(self, value):
        if not value.strip():
            raise serializers.ValidationError("Le nom de la menace ne peut pas être vide")
        return value.strip()
    
class OptimizationRequestSerializer(serializers.Serializer):
    """Serializer pour les requêtes d'optimisation"""
    architecture_id = serializers.UUIDField(required=True)
    budget_max = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Budget maximum pour l'optimisation (optionnel)"
    )
    include_implementation_plan = serializers.BooleanField(
        default=False,
        help_text="Créer automatiquement un plan d'implémentation"
    )
    responsable_id = serializers.UUIDField(
        required=False, 
        allow_null=True,
        help_text="Responsable par défaut pour les implémentations"
    )

class OptimizedMeasureSerializer(serializers.Serializer):
    """Serializer pour une mesure optimisée"""
    measure_id = serializers.UUIDField()
    measure_nom = serializers.CharField()
    measure_code = serializers.CharField()
    cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    efficacity = serializers.DecimalField(max_digits=5, decimal_places=2)
    nature = serializers.CharField()
    technique_nom = serializers.CharField()
    controle_code = serializers.CharField()
    selected = serializers.BooleanField()

# api/serializers.py

# Trouvez cette section et remplacez-la :

class AttributOptimizationResultSerializer(serializers.Serializer):
    """Serializer pour le résultat d'optimisation d'un attribut"""
    # ✅ TOUS les champs sont maintenant optionnels (required=False)
    actif_id = serializers.UUIDField(required=False)
    actif_nom = serializers.CharField(required=False)
    architecture_id = serializers.UUIDField(required=False)
    architecture_nom = serializers.CharField(required=False)
    attribut_id = serializers.UUIDField(required=False)  # ✅ Aussi optionnel
    attribut_type = serializers.CharField(required=False)  # ✅ Aussi optionnel
    status = serializers.CharField(required=False)  # ✅ Aussi optionnel
    
    # Résultats
    selected_measures = OptimizedMeasureSerializer(many=True, required=False)
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    total_efficacite = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    objective_value = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    measures_count = serializers.IntegerField(required=False)
    total_measures_available = serializers.IntegerField(required=False)
    measures_rejected = serializers.IntegerField(required=False)
    menaces_analyzed = serializers.IntegerField(required=False)
    risk_threshold = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    
    # Messages et erreurs
    message = serializers.CharField(required=False)
    error = serializers.CharField(required=False)


class GlobalOptimizationResultSerializer(serializers.Serializer):
    """Serializer pour le résultat d'optimisation globale"""
    status = serializers.CharField(required=False)  # ✅ Aussi optionnel
    selected_measures = serializers.ListField(child=serializers.UUIDField(), required=False)
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    total_efficacite = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    budget_used_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    measures_count = serializers.IntegerField(required=False)
    total_measures_analyzed = serializers.IntegerField(required=False)
    message = serializers.CharField(required=False)
    error = serializers.CharField(required=False)

class OptimizationRecommendationSerializer(serializers.Serializer):
    """Serializer pour les recommandations d'optimisation"""
    actif = serializers.CharField()
    attribut = serializers.CharField()
    measures_count = serializers.IntegerField()
    cost = serializers.DecimalField(max_digits=15, decimal_places=2)

class OptimizationSummarySerializer(serializers.Serializer):
    """Serializer pour le résumé des recommandations"""
    total_measures = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    measures_by_nature = serializers.DictField()
    recommendations = OptimizationRecommendationSerializer(many=True)

class FullOptimizationResultSerializer(serializers.Serializer):
    """Serializer pour le résultat complet d'optimisation"""
    architecture_id = serializers.UUIDField(required=False)  # ✅ Optionnel
    architecture_nom = serializers.CharField(required=False)
    optimization_type = serializers.CharField(required=False)  # ✅ Optionnel
    budget_max = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    total_actifs_processed = serializers.IntegerField(required=False)
    total_attributs_processed = serializers.IntegerField(required=False)
    successful_optimizations = serializers.IntegerField(required=False)
    total_measures_rejected = serializers.IntegerField(required=False)
    
    # Résultats individuels
    results = AttributOptimizationResultSerializer(many=True, required=False)
    recommended_measures = OptimizationSummarySerializer(required=False)
    
    # Optimisation globale (si applicable)
    global_optimization = GlobalOptimizationResultSerializer(required=False)
    
    # Plan d'implémentation (si créé)
    implementation_plan = serializers.DictField(required=False)
    
    # Erreurs
    error = serializers.CharField(required=False)

class ImplementationPlanSerializer(serializers.Serializer):
    """Serializer pour le plan d'implémentation"""
    status = serializers.CharField()
    implementations_created = serializers.IntegerField(required=False)
    implementation_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    error = serializers.CharField(required=False)

class OptimizationStatusSerializer(serializers.Serializer):
    """Serializer pour le statut de l'optimisation"""
    solver_available = serializers.BooleanField()
    solver_name = serializers.CharField()
    last_optimization_time = serializers.DateTimeField(required=False, allow_null=True)
    total_optimizations_run = serializers.IntegerField()
    architectures_optimized = serializers.IntegerField()
    
class QuickOptimizationSerializer(serializers.Serializer):
    """Serializer pour l'optimisation rapide d'un attribut"""
    attribut_securite_id = serializers.UUIDField(required=True)
    budget_max = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        required=False, 
        allow_null=True
    )
    create_implementations = serializers.BooleanField(default=False)
    responsable_id = serializers.UUIDField(required=False, allow_null=True)
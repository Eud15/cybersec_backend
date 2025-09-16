# api/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from decimal import Decimal
from .models import (
    TypeActif, Architecture, Actif, AttributSecurite, Menace, AttributMenace,
    ControleNIST, MenaceControle, Technique, MesureDeControle, 
    ImplementationMesure, LogActivite
)

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

class TypeActifSerializer(serializers.ModelSerializer):
    actifs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TypeActif
        fields = ['id', 'nom', 'description', 'actifs_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_actifs_count(self, obj):
        return obj.actifs.count()

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
    controle_code = serializers.CharField(source='technique.controle_nist.code', read_only=True)
    controle_nom = serializers.CharField(source='technique.controle_nist.nom', read_only=True)
    cout_total_3_ans_calculated = serializers.ReadOnlyField(source='cout_total_3_ans')
    implementations = ImplementationMesureSerializer(many=True, read_only=True)
    implementations_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MesureDeControle
        fields = [
            'id', 'mesure_code', 'nom', 'description', 'nature_mesure',  # mesure_code ajouté
            'cout_mise_en_oeuvre', 'cout_maintenance_annuel', 'efficacite',
            'duree_implementation', 'ressources_necessaires',
            'technique', 'technique_code', 'technique_nom', 'controle_code', 'controle_nom',
            'cout_total_3_ans_calculated', 'implementations', 'implementations_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_implementations_count(self, obj):
        return obj.implementations.count()

class MesureDeControleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MesureDeControle
        fields = [
            'technique', 'mesure_code', 'nom', 'description', 'nature_mesure',  # mesure_code ajouté
            'cout_mise_en_oeuvre', 'cout_maintenance_annuel', 'efficacite',
            'duree_implementation', 'ressources_necessaires'
        ]
    
    def validate_efficacite(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("L'efficacité doit être entre 0 et 100.")
        return value
    
    def validate_mesure_code(self, value):
        """Valide le format du code mesure"""
        if value:  # Seulement si un code est fourni
            # Optionnel: validation du format (ex: AC-2.1.01, SI-4.a.01)
            import re
            if not re.match(r'^[A-Z]{2,4}-\d+(\.[a-zA-Z0-9]+)*(\.\d+)*$', value):
                raise serializers.ValidationError(
                    "Le code mesure doit suivre le format: XX-N.x.nn (ex: AC-2.1.01, SI-4.a.01)"
                )
            
            return value.upper()
        return value

# ============================================================================
# SERIALIZERS POUR TECHNIQUES
# ============================================================================

class TechniqueSerializer(serializers.ModelSerializer):
    controle_code = serializers.CharField(source='controle_nist.code', read_only=True)
    controle_nom = serializers.CharField(source='controle_nist.nom', read_only=True)
    mesures_controle = MesureDeControleSerializer(many=True, read_only=True)
    mesures_count = serializers.SerializerMethodField()
    cout_moyen_mesures = serializers.SerializerMethodField()
    
    class Meta:
        model = Technique
        fields = [
            'id', 'technique_code', 'nom', 'description', 'type_technique', 'complexite',
            'controle_nist', 'controle_code', 'controle_nom',
            'mesures_controle', 'mesures_count', 'cout_moyen_mesures',
            'created_at'
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

class TechniqueCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technique
        fields = ['controle_nist', 'technique_code', 'nom', 'description', 'type_technique', 'complexite']
    
    def validate_technique_code(self, value):
        """Valide le format du code technique"""
        if not value:
            raise serializers.ValidationError("Le code technique est requis.")
        
        # Optionnel: validation du format (ex: AC-2.1, SI-4.a)
        import re
        if not re.match(r'^[A-Z]{2,4}-\d+(\.[a-zA-Z0-9]+)*$', value):
            raise serializers.ValidationError(
                "Le code technique doit suivre le format: XX-N.x (ex: AC-2.1, SI-4.a)"
            )
        
        return value.upper()
# ============================================================================
# SERIALIZERS POUR CONTROLES NIST
# ============================================================================

class ControleNISTSerializer(serializers.ModelSerializer):
    techniques = TechniqueSerializer(many=True, read_only=True)
    menaces_traitees = serializers.SerializerMethodField()
    techniques_count = serializers.SerializerMethodField()
    mesures_count_total = serializers.SerializerMethodField()
    cout_total_implementation = serializers.SerializerMethodField()
    efficacite_moyenne = serializers.SerializerMethodField()
    
    class Meta:
        model = ControleNIST
        fields = [
            'id', 'code', 'nom', 'description', 'famille', 'priorite',
            'techniques', 'menaces_traitees', 'techniques_count', 'mesures_count_total',
            'cout_total_implementation', 'efficacite_moyenne', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_menaces_traitees(self, obj):
        """Retourne les menaces traitées par ce contrôle"""
        menaces_links = obj.menaces_traitees.select_related('menace').all()
        return [{
            'menace_id': link.menace.id,
            'menace_nom': link.menace.nom,
            'menace_severite': link.menace.severite,
            'efficacite': float(link.efficacite),
            'statut_conformite': link.statut_conformite,
            'commentaires': link.commentaires
        } for link in menaces_links]
    
    def get_techniques_count(self, obj):
        return obj.techniques.count()
    
    def get_mesures_count_total(self, obj):
        return sum(tech.mesures_controle.count() for tech in obj.techniques.all())
    
    def get_cout_total_implementation(self, obj):
        """Coût total de toutes les mesures du contrôle"""
        total = 0
        for technique in obj.techniques.all():
            for mesure in technique.mesures_controle.all():
                total += mesure.cout_total_3_ans
        return round(total, 2)
    
    def get_efficacite_moyenne(self, obj):
        """Efficacité moyenne des mesures du contrôle"""
        mesures = []
        for technique in obj.techniques.all():
            mesures.extend(technique.mesures_controle.all())
        
        if not mesures:
            return 0
        
        efficacites = [float(m.efficacite) for m in mesures if m.efficacite]
        return round(sum(efficacites) / len(efficacites), 2) if efficacites else 0

class ControleNISTListSerializer(serializers.ModelSerializer):
    techniques_count = serializers.SerializerMethodField()
    menaces_traitees_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ControleNIST
        fields = [
            'id', 'code', 'nom', 'description', 'famille', 'priorite',
            'techniques_count', 'menaces_traitees_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_techniques_count(self, obj):
        return obj.techniques.count()
    
    def get_menaces_traitees_count(self, obj):
        return obj.menaces_traitees.count()

# ============================================================================
# SERIALIZERS POUR MENACE-CONTROLE
# ============================================================================

class MenaceControleSerializer(serializers.ModelSerializer):
    controle_code = serializers.CharField(source='controle_nist.code', read_only=True)
    controle_nom = serializers.CharField(source='controle_nist.nom', read_only=True)
    controle_famille = serializers.CharField(source='controle_nist.famille', read_only=True)
    controle_detail = ControleNISTSerializer(source='controle_nist', read_only=True)
    
    class Meta:
        model = MenaceControle
        fields = [
            'id', 'menace', 'controle_nist', 'controle_code', 'controle_nom', 
            'controle_famille', 'efficacite', 'statut_conformite', 'commentaires',
            'controle_detail', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class MenaceControleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenaceControle
        fields = ['menace', 'controle_nist', 'efficacite', 'statut_conformite', 'commentaires']

# ============================================================================
# SERIALIZERS POUR MENACES
# ============================================================================

class MenaceSerializer(serializers.ModelSerializer):
    controles_nist = MenaceControleSerializer(many=True, read_only=True)
    attributs_impactes_count = serializers.SerializerMethodField()
    
    # Informations hiérarchiques ajoutées
    architecture_id = serializers.SerializerMethodField()
    architecture_nom = serializers.SerializerMethodField()
    actif_id = serializers.SerializerMethodField()
    actif_nom = serializers.SerializerMethodField()
    attribut_securite_id = serializers.SerializerMethodField()
    attribut_type = serializers.SerializerMethodField()
    
    # Métriques consolidées
    total_controles = serializers.SerializerMethodField()
    total_techniques = serializers.SerializerMethodField()
    total_mesures = serializers.SerializerMethodField()
    cout_total_protection = serializers.SerializerMethodField()
    taux_conformite = serializers.SerializerMethodField()
    
    class Meta:
        model = Menace
        fields = [
            'id', 'nom', 'description', 'type_menace', 'severite',
            
            # Hiérarchie parent ajoutée
            'architecture_id', 'architecture_nom',
            'actif_id', 'actif_nom', 
            'attribut_securite_id', 'attribut_type',
            
            # Relations et métriques
            'controles_nist', 'attributs_impactes_count',
            'total_controles', 'total_techniques', 'total_mesures',
            'cout_total_protection', 'taux_conformite',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def _get_attribut_principal(self, obj):
        """Méthode helper pour récupérer l'attribut principal"""
        # Prendre le premier attribut associé (par ordre de création ou d'importance)
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
    
    def get_total_controles(self, obj):
        return obj.controles_nist.count()
    
    def get_total_techniques(self, obj):
        total = 0
        for controle_link in obj.controles_nist.all():
            total += controle_link.controle_nist.techniques.count()
        return total
    
    def get_total_mesures(self, obj):
        total = 0
        for controle_link in obj.controles_nist.all():
            for technique in controle_link.controle_nist.techniques.all():
                total += technique.mesures_controle.count()
        return total
    
    def get_cout_total_protection(self, obj):
        total = 0
        for controle_link in obj.controles_nist.all():
            for technique in controle_link.controle_nist.techniques.all():
                for mesure in technique.mesures_controle.all():
                    total += mesure.cout_total_3_ans
        return round(total, 2)
    
    def get_taux_conformite(self, obj):
        controles = obj.controles_nist.all()
        if not controles:
            return 0
        conformes = controles.filter(statut_conformite='CONFORME').count()
        return round((conformes / controles.count()) * 100, 2)

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


class MenaceListSerializer(serializers.ModelSerializer):
    attributs_impactes_count = serializers.SerializerMethodField()
    controles_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Menace
        fields = [
            'id', 'nom', 'description', 'type_menace', 'severite',
            'attributs_impactes_count', 'controles_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_attributs_impactes_count(self, obj):
        return obj.attributs_impactes.count()
    
    def get_controles_count(self, obj):
        return obj.controles_nist.count()




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
        
        for controle_link in obj.menace.controles_nist.all():
            for technique in controle_link.controle_nist.techniques.all():
                for mesure in technique.mesures_controle.all():
                    if mesure.efficacite and mesure.cout_total_3_ans > 0:
                        ratio_efficacite_cout = float(mesure.efficacite) / mesure.cout_total_3_ans
                        solutions.append({
                            'mesure_id': mesure.id,
                            'mesure_nom': mesure.nom,
                            'technique_nom': technique.nom,
                            'controle_code': controle_link.controle_nist.code,
                            'efficacite': float(mesure.efficacite),
                            'cout_3_ans': mesure.cout_total_3_ans,
                            'ratio_efficacite_cout': round(ratio_efficacite_cout, 4),
                            'duree_implementation': mesure.duree_implementation,
                            'nature_mesure': mesure.nature_mesure,
                            'statut_conformite': controle_link.statut_conformite
                        })
        
        # Trier par ratio efficacité/coût décroissant et prendre les 3 premiers
        solutions.sort(key=lambda x: x['ratio_efficacite_cout'], reverse=True)
        return solutions[:3]

class AttributMenaceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributMenace
        fields = ['attribut_securite', 'menace', 'probabilite', 'impact', 'cout_impact']
    
    def validate_probabilite(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("La probabilité doit être entre 0 et 100.")
        return value
    
    def validate_impact(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("L'impact doit être entre 0 et 100.")
        return value

# ============================================================================
# SERIALIZERS POUR ATTRIBUTS DE SECURITE
# ============================================================================

class AttributSecuriteSerializer(serializers.ModelSerializer):
    actif_nom = serializers.CharField(source='actif.nom', read_only=True)
    actif_architecture = serializers.CharField(source='actif.architecture.nom', read_only=True)
    menaces = AttributMenaceSerializer(many=True, read_only=True)
    risque_financier_attribut = serializers.ReadOnlyField()
    ratio_risque_cout = serializers.ReadOnlyField()
    niveau_alerte = serializers.ReadOnlyField()
    
    # Analyses consolidées
    cout_protection_recommande = serializers.SerializerMethodField()
    economies_potentielles = serializers.SerializerMethodField()
    
    class Meta:
        model = AttributSecurite
        fields = [
            'id', 'actif', 'actif_nom', 'actif_architecture', 'type_attribut',
            'cout_compromission', 'priorite', 'risque_financier_attribut',
            'ratio_risque_cout', 'niveau_alerte', 'menaces',
            'cout_protection_recommande', 'economies_potentielles',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_cout_protection_recommande(self, obj):
        """Estime le coût de protection recommandé"""
        cout_total = 0
        menaces_traitees = set()
        
        for menace_link in obj.menaces.all():
            if menace_link.menace.id not in menaces_traitees:
                menaces_traitees.add(menace_link.menace.id)
                
                # Trouver la mesure la plus efficace pour cette menace
                controles = menace_link.menace.controles_nist.all()
                for controle_link in controles:
                    for technique in controle_link.controle_nist.techniques.all():
                        mesures = technique.mesures_controle.all()
                        if mesures:
                            # Prendre la mesure avec le meilleur ratio efficacité/coût
                            meilleure_mesure = min(
                                mesures,
                                key=lambda m: m.cout_total_3_ans / max(float(m.efficacite), 1),
                                default=None
                            )
                            if meilleure_mesure:
                                cout_total += meilleure_mesure.cout_total_3_ans
                                break
        
        return round(cout_total, 2)
    
    def get_economies_potentielles(self, obj):
        """Calcule les économies potentielles"""
        risque_actuel = obj.risque_financier_attribut
        cout_protection = self.get_cout_protection_recommande(obj)
        
        # Supposer une réduction de 80% du risque après protection
        risque_apres_protection = risque_actuel * 0.2
        reduction_risque = risque_actuel - risque_apres_protection
        
        return {
            'reduction_risque_annuelle': round(reduction_risque, 2),
            'cout_protection_3_ans': cout_protection,
            'benefice_net_3_ans': round((reduction_risque * 3) - cout_protection, 2),
            'roi_pourcentage': round(
                (((reduction_risque * 3) - cout_protection) / cout_protection) * 100, 2
            ) if cout_protection > 0 else 0
        }

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
    total_controles_nist = serializers.IntegerField()
    total_techniques = serializers.IntegerField()
    total_mesures = serializers.IntegerField()
    
    # Risques financiers
    risque_financier_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    architectures_hors_tolerance = serializers.IntegerField()
    budget_risque_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Conformité
    taux_conformite_moyen = serializers.DecimalField(max_digits=5, decimal_places=2)
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
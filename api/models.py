# api/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

class BaseModel(models.Model):
    """Modèle de base avec timestamp"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class TypeActif(BaseModel):
    """Type d'actif (serveur, réseau, application, base de données...)"""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'type_actif'
        verbose_name = 'Type d\'actif'
        verbose_name_plural = 'Types d\'actifs'
    
    def __str__(self):
        return self.nom

class Architecture(BaseModel):
    """Architecture système"""
    nom = models.CharField(max_length=200)
    description = models.TextField()
    risque_tolere = models.DecimalField(
        max_digits=15,  # Augmenté pour supporter de gros montants
        decimal_places=2, 
        validators=[MinValueValidator(0)],  # Suppression de MaxValueValidator
        help_text="Coût maximal du risque toléré (en €)",
        default=Decimal('10000.00')  # Valeur par défaut plus réaliste en €
    )
    
    class Meta:
        db_table = 'architecture'
        verbose_name = 'Architecture'
        verbose_name_plural = 'Architectures'
    
    def __str__(self):
        return self.nom
    
    @property
    def risque_financier_total(self):
        """Calcule le risque financier total de l'architecture"""
        total_risque_financier = 0
        for actif in self.actifs.all():
            for attr_secu in actif.attributs_securite.all():
                for menace_link in attr_secu.menaces.all():
                    total_risque_financier += menace_link.risque_financier
        return float(total_risque_financier)
    
    @property
    def risque_depasse_tolerance(self):
        """Vérifie si le risque financier total dépasse la tolérance"""
        return self.risque_financier_total > float(self.risque_tolere)
    
    @property
    def pourcentage_tolerance_utilise(self):
        """Calcule le pourcentage de tolérance au risque utilisée"""
        if float(self.risque_tolere) == 0:
            return 100.0 if self.risque_financier_total > 0 else 0.0
        return min(100.0, (self.risque_financier_total / float(self.risque_tolere)) * 100)

class Actif(BaseModel):
    """Actif appartenant à une architecture"""
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    cout = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    type_actif = models.ForeignKey(TypeActif, on_delete=models.PROTECT, related_name='actifs')
    architecture = models.ForeignKey(Architecture, on_delete=models.CASCADE, related_name='actifs')
    proprietaire = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    criticite = models.CharField(
        max_length=10,
        choices=[
            ('FAIBLE', 'Faible'),
            ('MOYEN', 'Moyen'),
            ('ELEVE', 'Élevé'),
            ('CRITIQUE', 'Critique')
        ],
        default='MOYEN'
    )
    
    class Meta:
        db_table = 'actif'
        verbose_name = 'Actif'
        verbose_name_plural = 'Actifs'
    
    def __str__(self):
        return f"{self.nom} ({self.architecture.nom})"

class AttributSecurite(BaseModel):
    """Attributs de sécurité d'un actif (CIA Triad + autres)"""
    actif = models.ForeignKey(Actif, on_delete=models.CASCADE, related_name='attributs_securite')
    type_attribut = models.CharField(
        max_length=20,
        choices=[
            ('CONFIDENTIALITE', 'Confidentialité'),
            ('INTEGRITE', 'Intégrité'),
            ('DISPONIBILITE', 'Disponibilité'),
            ('AUTHENTIFICATION', 'Authentification'),
            ('AUTORISATION', 'Autorisation'),
            ('NON_REPUDIATION', 'Non-répudiation')
        ]
    )
    cout_compromission = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Coût financier en cas de compromission de cet attribut (en €)",
        default=Decimal('0.00')
    )

    priorite = models.CharField(
        max_length=10,
        choices=[
            ('P0', 'P0 - Critique'),
            ('P1', 'P1 - Haute'),
            ('P2', 'P2 - Moyenne'),
            ('P3', 'P3 - Basse')
        ],
        default='P2'
    )
    
    @property
    def risque_financier_attribut(self):
        """Calcule le risque financier total pour cet attribut basé sur ses menaces"""
        total_risque = 0
        for menace_link in self.menaces.all():
            total_risque += menace_link.risque_financier
        return float(total_risque)
    
    @property
    def ratio_risque_cout(self):
        """Ratio entre le risque calculé et le coût de compromission défini"""
        if float(self.cout_compromission) == 0:
            return 0.0
        return self.risque_financier_attribut / float(self.cout_compromission)
    
    @property
    def niveau_alerte(self):
        """Niveau d'alerte basé sur le ratio risque/coût"""
        ratio = self.ratio_risque_cout
        if ratio >= 1.0:
            return 'CRITIQUE'
        elif ratio >= 0.7:
            return 'ELEVE'
        elif ratio >= 0.4:
            return 'MOYEN'
        else:
            return 'FAIBLE'
    
    class Meta:
        db_table = 'attribut_securite'
        verbose_name = 'Attribut de sécurité'
        verbose_name_plural = 'Attributs de sécurité'
        unique_together = ['actif', 'type_attribut']
    
    def __str__(self):
        return f"{self.actif.nom} - {self.type_attribut}"

# api/models.py - Ajout dans la classe Menace

class Menace(BaseModel):
    """Menaces de sécurité liées aux attributs"""
    nom = models.CharField(max_length=200)
    description = models.TextField()
    type_menace = models.CharField(
        max_length=50,
        choices=[
            ('Spoofing', 'S - Usurpation d\'identité'),
            ('Tampering', 'T - Altération des données'),
            ('Repudiation', 'R - Répudiation'),
            ('Information Disclosure', 'I - Divulgation d\'informations'),
            ('Denial of Service (DoS)', 'D - Déni de service'),
            ('Elevation of Privilege', 'E - Élévation de privilèges'),
            ('AUTRE', 'Autre')
        ],
        default='Spoofing'  # Nouvelle valeur par défaut
    )
    severite = models.CharField(
        max_length=10,
        choices=[
            ('FAIBLE', 'Faible'),
            ('MOYEN', 'Moyen'),
            ('ELEVE', 'Élevé'),
            ('CRITIQUE', 'Critique')
        ]
    )
    
    # Nouveaux champs optionnels pour définir un contexte principal
    attribut_securite_principal = models.ForeignKey(
        'AttributSecurite', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='menaces_principales',
        help_text="Attribut de sécurité principal pour cette menace"
    )
    
    class Meta:
        db_table = 'menace'
        verbose_name = 'Menace'
        verbose_name_plural = 'Menaces'
    
    def __str__(self):
        return f"{self.nom} ({self.severite})"
    

    @property 
    def attribut_securite_parent_simple(self):
        """Version alternative qui trie en Python"""
        if self.attribut_securite_principal:
            return self.attribut_securite_principal
        
        # Récupérer tous et trier en Python
        attr_menaces = list(self.attributs_impactes.select_related('attribut_securite').all())
        if not attr_menaces:
            return None
        
        # Trier par risque financier (propriété calculée)
        attr_menaces.sort(key=lambda am: am.risque_financier, reverse=True)
        return attr_menaces[0].attribut_securite
    @property
    def actif_parent(self):
        """Retourne l'actif parent"""
        attribut = self.attribut_securite_parent
        return attribut.actif if attribut else None
    
    @property
    def architecture_parent(self):
        """Retourne l'architecture parent"""
        actif = self.actif_parent
        return actif.architecture if actif else None
    
    @property
    def attribut_nom(self):
        """Nom de l'attribut parent"""
        attribut = self.attribut_securite_parent
        return attribut.actif.nom if attribut else None
    
    @property
    def attribut_type(self):
        """Type de l'attribut parent"""
        attribut = self.attribut_securite_parent
        return attribut.type_attribut if attribut else None
    
    @property
    def actif_nom(self):
        """Nom de l'actif parent"""
        actif = self.actif_parent
        return actif.nom if actif else None
    
    @property
    def actif_id(self):
        """ID de l'actif parent"""
        actif = self.actif_parent
        return actif.id if actif else None
    
    @property
    def architecture_nom(self):
        """Nom de l'architecture parent"""
        architecture = self.architecture_parent
        return architecture.nom if architecture else None
    
    @property
    def architecture_id(self):
        """ID de l'architecture parent"""
        architecture = self.architecture_parent
        return architecture.id if architecture else None
    
    @property
    def attribut_securite_id(self):
        """ID de l'attribut de sécurité parent"""
        attribut = self.attribut_securite_parent
        return attribut.id if attribut else None
    
    @property
    def contexte_hierarchique_complet(self):
        """Retourne le contexte hiérarchique complet"""
        attribut = self.attribut_securite_parent
        if not attribut:
            return None
        
        return {
            'architecture': {
                'id': str(attribut.actif.architecture.id),
                'nom': attribut.actif.architecture.nom
            },
            'actif': {
                'id': str(attribut.actif.id),
                'nom': attribut.actif.nom,
                'criticite': attribut.actif.criticite
            },
            'attribut_securite': {
                'id': str(attribut.id),
                'type_attribut': attribut.type_attribut,
                'priorite': attribut.priorite
            }
        }
    
    @property
    def risque_financier_dans_contexte(self):
        """Risque financier de cette menace dans le contexte principal"""
        if not self.attribut_securite_parent:
            return 0
        
        attr_menace = self.attributs_impactes.filter(
            attribut_securite=self.attribut_securite_parent
        ).first()
        
        return attr_menace.risque_financier if attr_menace else 0
    
    @property
    def probabilite(self):
        """Probabilité dans le contexte principal"""
        if not self.attribut_securite_parent:
            return None
        
        attr_menace = self.attributs_impactes.filter(
            attribut_securite=self.attribut_securite_parent
        ).first()
        
        return attr_menace.probabilite if attr_menace else None
    
    @property
    def impact(self):
        """Impact dans le contexte principal"""
        if not self.attribut_securite_parent:
            return None
        
        attr_menace = self.attributs_impactes.filter(
            attribut_securite=self.attribut_securite_principal
        ).first()
        
        return attr_menace.impact if attr_menace else None
    
    @property
    def cout_impact(self):
        """Coût d'impact dans le contexte principal"""
        if not self.attribut_securite_parent:
            return None
        
        attr_menace = self.attributs_impactes.filter(
            attribut_securite=self.attribut_securite_principal
        ).first()
        
        return attr_menace.cout_impact if attr_menace else None
    
    @property
    def niveau_risque_calculated(self):
        """Niveau de risque calculé dans le contexte principal"""
        if not self.attribut_securite_parent:
            return None
        
        attr_menace = self.attributs_impactes.filter(
            attribut_securite=self.attribut_securite_principal
        ).first()
        
        return attr_menace.niveau_risque if attr_menace else None
    
    @property
    def risque_financier_calculated(self):
        """Risque financier calculé dans le contexte principal"""
        if not self.attribut_securite_parent:
            return None
        
        attr_menace = self.attributs_impactes.filter(
            attribut_securite=self.attribut_securite_principal
        ).first()
        
        return attr_menace.risque_financier if attr_menace else None

class AttributMenace(BaseModel):
    """Association entre un attribut de sécurité et une menace"""
    attribut_securite = models.ForeignKey(AttributSecurite, on_delete=models.CASCADE, related_name='menaces')
    menace = models.ForeignKey(Menace, on_delete=models.CASCADE, related_name='attributs_impactes')
    
    # Évaluation du risque
    probabilite = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Probabilité d'occurrence (0-100%)",
        default=Decimal('0.00')
    )
    impact = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Impact sur l'attribut de sécurité (0-100%)",
        default=Decimal('0.00')
    )
    cout_impact = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Coût financier estimé de l'impact"
    )
    
    @property
    def niveau_risque(self):
        """Calcule le niveau de risque : Probabilité × Impact"""
        probabilite = self.probabilite if self.probabilite is not None else Decimal('0.00')
        impact = self.impact if self.impact is not None else Decimal('0.00')
        return float((probabilite * impact) / 100)
    
    @property
    def risque_financier(self):
        """Calcule le risque financier : Probabilité × Coût Impact"""
        probabilite = self.probabilite if self.probabilite is not None else Decimal('0.00')
        cout_impact = self.cout_impact if self.cout_impact is not None else Decimal('0.00')
        return float((probabilite / 100) * cout_impact)
    
    class Meta:
        db_table = 'attribut_menace'
        verbose_name = 'Attribut-Menace'
        verbose_name_plural = 'Attributs-Menaces'
        unique_together = ['attribut_securite', 'menace']
    
    def __str__(self):
        return f"{self.attribut_securite} → {self.menace.nom}"

class ControleNIST(BaseModel):
    """Contrôles NIST"""
    code = models.CharField(max_length=20, unique=True)  
    nom = models.CharField(max_length=200)
    description = models.TextField(
        null=True, 
        blank=True,
        help_text="Description détaillée du contrôle NIST"
    )
    famille = models.CharField(max_length=100)  
    priorite = models.CharField(
        max_length=10,
        choices=[
            ('P0', 'P0 - Critique'),
            ('P1', 'P1 - Haute'),
            ('P2', 'P2 - Moyenne'),
            ('P3', 'P3 - Basse')
        ],
        default='P2',
        null=True,  
        blank=True  
    )
    
    class Meta:
        db_table = 'controle_nist'
        verbose_name = 'Contrôle NIST'
        verbose_name_plural = 'Contrôles NIST'
    
    def __str__(self):
        return f"{self.code} - {self.nom}"
class MenaceControle(BaseModel):
    """Association entre une menace et les contrôles NIST qui la traitent"""
    menace = models.ForeignKey(Menace, on_delete=models.CASCADE, related_name='controles_nist')
    controle_nist = models.ForeignKey(ControleNIST, on_delete=models.CASCADE, related_name='menaces_traitees')
    
    # Efficacité du contrôle contre cette menace
    efficacite = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Efficacité du contrôle contre cette menace (0-100%)",
        default=Decimal('0.00')
    )
    
    statut_conformite = models.CharField(
        max_length=20,
        choices=[
            ('NON_CONFORME', 'Non conforme'),
            ('PARTIELLEMENT', 'Partiellement conforme'),
            ('CONFORME', 'Conforme'),
            ('NON_APPLICABLE', 'Non applicable')
        ],
        default='NON_CONFORME'
    )
    
    commentaires = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'menace_controle'
        verbose_name = 'Menace-Contrôle'
        verbose_name_plural = 'Menaces-Contrôles'
        unique_together = ['menace', 'controle_nist']
    
    def __str__(self):
        return f"{self.menace.nom} → {self.controle_nist.code}"

class Technique(BaseModel):
    """Techniques d'implémentation pour un contrôle NIST"""
    controle_nist = models.ForeignKey(ControleNIST, on_delete=models.CASCADE, related_name='techniques')
    technique_code = models.CharField(max_length=20, unique=True,null=True, 
        blank=True, help_text="Code unique de la technique (ex: AC-2.1, SI-4.a)")
    nom = models.CharField(max_length=200)
    description = models.TextField()
    type_technique = models.CharField(
        max_length=50,
        choices=[
            ('TECHNIQUE', 'Technique'),
            ('ADMINISTRATIF', 'Administratif'),
            ('PHYSIQUE', 'Physique'),
            ('PREVENTIF', 'Préventif'),
            ('DETECTIF', 'Détectif'),
            ('CORRECTIF', 'Correctif')
        ]
    )
    complexite = models.CharField(
        max_length=10,
        choices=[
            ('FAIBLE', 'Faible'),
            ('MOYEN', 'Moyen'),
            ('ELEVE', 'Élevé')
        ],
        default='MOYEN'
    )
    
    class Meta:
        db_table = 'technique'
        verbose_name = 'Technique'
        verbose_name_plural = 'Techniques'
    
    def __str__(self):
        return f"{self.technique_code} - {self.nom}"
class MesureDeControle(BaseModel):
    """Mesures de contrôle concrètes pour implémenter une technique"""
    technique = models.ForeignKey(Technique, on_delete=models.CASCADE, related_name='mesures_controle')
    nom = models.CharField(max_length=200)
    description = models.TextField()
    mesure_code = models.CharField(
        max_length=30, 
        
        null=True, 
        blank=True, 
        help_text="Code unique de la mesure (ex: AC-2.1.01, SI-4.a.01)"
    )
    
    # Nature de la mesure
    nature_mesure = models.CharField(
        max_length=50,
        choices=[
            ('ORGANISATIONNEL', 'Organisationnel'),
            ('TECHNIQUE', 'Technique'),
            ('PHYSIQUE', 'Physique'),
            ('JURIDIQUE', 'Juridique')
        ]
    )
    
    # Coûts et efficacité
    cout_mise_en_oeuvre = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Coût initial d'implémentation"
    )
    cout_maintenance_annuel = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Coût de maintenance annuel"
    )
    efficacite = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Efficacité de la mesure (0-100%)",
        default=Decimal('0.00')
    )
    
    # Temps et ressources
    duree_implementation = models.IntegerField(
        default=30,
        help_text="Durée d'implémentation en jours"
    )
    ressources_necessaires = models.TextField(
        blank=True, 
        null=True,
        help_text="Description des ressources humaines/techniques nécessaires"
    )
    
    class Meta:
        db_table = 'mesure_de_controle'
        verbose_name = 'Mesure de contrôle'
        verbose_name_plural = 'Mesures de contrôle'
    
    def __str__(self):
        return f"{self.technique.controle_nist.code} - {self.nom}"
    
    @property
    def cout_total_3_ans(self):
        """Calcule le coût total sur 3 ans"""
        cout_mise_en_oeuvre = self.cout_mise_en_oeuvre if self.cout_mise_en_oeuvre is not None else Decimal('0.00')
        cout_maintenance_annuel = self.cout_maintenance_annuel if self.cout_maintenance_annuel is not None else Decimal('0.00')
        return float(cout_mise_en_oeuvre + (cout_maintenance_annuel * 3))

class ImplementationMesure(BaseModel):
    """Suivi de l'implémentation d'une mesure pour un attribut spécifique"""
    attribut_menace = models.ForeignKey(
        AttributMenace, 
        on_delete=models.CASCADE, 
        related_name='implementations'
    )
    mesure_controle = models.ForeignKey(
        MesureDeControle, 
        on_delete=models.CASCADE, 
        related_name='implementations'
    )
    
    # Statut de l'implémentation
    statut = models.CharField(
        max_length=20,
        choices=[
            ('PLANIFIE', 'Planifié'),
            ('EN_COURS', 'En cours'),
            ('IMPLEMENTE', 'Implémenté'),
            ('VERIFIE', 'Vérifié'),
            ('ANNULE', 'Annulé')
        ],
        default='PLANIFIE'
    )
    
    # Planification
    date_debut_prevue = models.DateTimeField(null=True, blank=True)
    date_fin_prevue = models.DateTimeField(null=True, blank=True)
    date_implementation = models.DateTimeField(null=True, blank=True)
    
    # Responsabilités
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    equipe = models.TextField(blank=True, null=True, help_text="Membres de l'équipe impliqués")
    
    # Suivi
    pourcentage_avancement = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=Decimal('0.00')
    )
    commentaires = models.TextField(blank=True, null=True)
    obstacles = models.TextField(blank=True, null=True, help_text="Obstacles rencontrés")
    
    @property
    def risque_residuel(self):
        """Calcule le risque résiduel après implémentation"""
        if self.statut in ['IMPLEMENTE', 'VERIFIE']:
            risque_initial = self.attribut_menace.niveau_risque
            efficacite = self.mesure_controle.efficacite if self.mesure_controle.efficacite is not None else Decimal('0.00')
            reduction = float(efficacite / 100) * risque_initial
            return max(0, risque_initial - reduction)
        return self.attribut_menace.niveau_risque
    
    class Meta:
        db_table = 'implementation_mesure'
        verbose_name = 'Implémentation de mesure'
        verbose_name_plural = 'Implémentations de mesures'
        unique_together = ['attribut_menace', 'mesure_controle']
    
    def __str__(self):
        return f"{self.mesure_controle.nom} → {self.attribut_menace}"

class LogActivite(BaseModel):
    """Logs des activités système"""
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    objet_type = models.CharField(max_length=100)  # Type d'objet modifié
    objet_id = models.CharField(max_length=100)    # ID de l'objet
    details = models.JSONField(default=dict, blank=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'log_activite'
        verbose_name = 'Log d\'activité'
        verbose_name_plural = 'Logs d\'activité'
        ordering = ['-created_at']
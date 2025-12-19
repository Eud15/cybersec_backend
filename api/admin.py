# api/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CategorieActif, TypeActif, Architecture, Actif, AttributSecurite, 
    Menace, AttributMenace, MenaceMesure, Technique, MesureDeControle, 
    ImplementationMesure, LogActivite
)


# ============================================================================
# ADMIN POUR CATÉGORIE ET TYPE D'ACTIF
# ============================================================================

class TypeActifInline(admin.TabularInline):
    model = TypeActif
    extra = 0
    fields = ['nom', 'code', 'description', 'actifs_count']
    readonly_fields = ['actifs_count']
    
    def actifs_count(self, obj):
        if obj.pk:
            return obj.actifs.count()
        return 0
    actifs_count.short_description = 'Nb Actifs'


@admin.register(CategorieActif)
class CategorieActifAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'types_count', 'actifs_total_count', 'created_at']
    search_fields = ['nom', 'code', 'description']
    ordering = ['nom']
    inlines = [TypeActifInline]
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('nom', 'code', 'description')
        }),
    )
    
    def types_count(self, obj):
        return obj.types_actifs.count()
    types_count.short_description = 'Nb Types'
    
    def actifs_total_count(self, obj):
        return sum(type_actif.actifs.count() for type_actif in obj.types_actifs.all())
    actifs_total_count.short_description = 'Total Actifs'


@admin.register(TypeActif)
class TypeActifAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'categorie', 'actifs_count', 'created_at']
    list_filter = ['categorie']
    search_fields = ['nom', 'code', 'description', 'categorie__nom']
    ordering = ['categorie', 'nom']
    
    fieldsets = (
        ('Catégorie', {
            'fields': ('categorie',)
        }),
        ('Informations du type', {
            'fields': ('nom', 'code', 'description')
        }),
    )
    
    def actifs_count(self, obj):
        return obj.actifs.count()
    actifs_count.short_description = 'Nb Actifs'


# ============================================================================
# ADMIN POUR ARCHITECTURES
# ============================================================================

class ActifInline(admin.TabularInline):
    model = Actif
    extra = 0
    fields = ['nom', 'type_actif', 'cout', 'criticite', 'proprietaire']
    readonly_fields = []


@admin.register(Architecture)
class ArchitectureAdmin(admin.ModelAdmin):
    list_display = [
        'nom', 'risque_tolere_formatted', 'actifs_count', 
        'risque_financier_total_display', 'tolerance_status', 'created_at'
    ]
    search_fields = ['nom', 'description']
    inlines = [ActifInline]
    ordering = ['nom']
    
    def risque_tolere_formatted(self, obj):
        return '{:,.2f} $'.format(obj.risque_tolere)
    risque_tolere_formatted.short_description = 'Tolérance Risque'
    
    def actifs_count(self, obj):
        return obj.actifs.count()
    actifs_count.short_description = 'Nb Actifs'
    
    def risque_financier_total_display(self, obj):
        total = obj.risque_financier_total
        return '{:,.2f} $'.format(total)
    risque_financier_total_display.short_description = 'Risque Total'
    
    def tolerance_status(self, obj):
        pourcentage = obj.pourcentage_tolerance_utilise
        if obj.risque_depasse_tolerance:
            return format_html(
                '<span style="color: red; font-weight: bold;">DÉPASSÉ ({:.1f}%)</span>',
                pourcentage
            )
        else:
            color = 'orange' if pourcentage > 80 else 'green'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, pourcentage
            )
    tolerance_status.short_description = 'Statut Tolérance'


# ============================================================================
# ADMIN POUR ACTIFS
# ============================================================================

class AttributSecuriteInline(admin.TabularInline):
    model = AttributSecurite
    extra = 0
    fields = ['type_attribut', 'cout_compromission', 'priorite', 'niveau_alerte_display', 'ratio_display']
    readonly_fields = ['niveau_alerte_display', 'ratio_display']
    
    def niveau_alerte_display(self, obj):
        if obj.pk:
            niveau = obj.niveau_alerte
            colors = {
                'FAIBLE': 'green',
                'MOYEN': 'orange', 
                'ELEVE': 'red',
                'CRITIQUE': 'darkred'
            }
            color = colors.get(niveau, 'black')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, niveau
            )
        return "N/A"
    niveau_alerte_display.short_description = 'Alerte'
    
    def ratio_display(self, obj):
        if obj.pk:
            ratio = obj.ratio_risque_cout
            if ratio >= 1.0:
                color = 'darkred'
            elif ratio >= 0.7:
                color = 'red'
            elif ratio >= 0.4:
                color = 'orange'
            else:
                color = 'green'
                
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.2f}</span>',
                color, ratio
            )
        return "N/A"
    ratio_display.short_description = 'Ratio'


@admin.register(Actif)
class ActifAdmin(admin.ModelAdmin):
    list_display = [
        'nom', 'type_actif', 'type_categorie', 'architecture', 
        'cout_formatted', 'criticite', 'proprietaire', 
        'attributs_count', 'risque_total'
    ]
    list_filter = ['type_actif__categorie', 'type_actif', 'architecture', 'criticite', 'proprietaire']
    search_fields = ['nom', 'description', 'type_actif__nom', 'type_actif__categorie__nom']
    ordering = ['architecture', 'nom']
    inlines = [AttributSecuriteInline]
    
    def type_categorie(self, obj):
        return obj.type_actif.categorie.nom
    type_categorie.short_description = 'Catégorie'
    
    def cout_formatted(self, obj):
        return '{:,.2f} $'.format(obj.cout)
    cout_formatted.short_description = 'Coût'
    
    def attributs_count(self, obj):
        return obj.attributs_securite.count()
    attributs_count.short_description = 'Nb Attributs'
    
    def risque_total(self, obj):
        total = 0
        for attr_secu in obj.attributs_securite.all():
            total += attr_secu.risque_financier_attribut
        return '{:,.2f} $'.format(total)
    risque_total.short_description = 'Risque Total'


# ============================================================================
# ADMIN POUR ATTRIBUTS DE SÉCURITÉ
# ============================================================================

class AttributMenaceInline(admin.TabularInline):
    model = AttributMenace
    extra = 0
    fields = ['menace', 'probabilite', 'impact', 'cout_impact', 'niveau_risque_display', 'risque_financier_display']
    readonly_fields = ['niveau_risque_display', 'risque_financier_display']
    
    def niveau_risque_display(self, obj):
        if obj.pk:
            risk_level = obj.niveau_risque
            if risk_level > 75:
                color = 'red'
            elif risk_level > 50:
                color = 'orange'
            else:
                color = 'green'
                
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.2f}</span>',
                color, risk_level
            )
        return "N/A"
    niveau_risque_display.short_description = 'Niveau Risque'
    
    def risque_financier_display(self, obj):
        if obj.pk:
            return '{:,.2f} $'.format(obj.risque_financier)
        return "N/A"
    risque_financier_display.short_description = 'Risque $'


@admin.register(AttributSecurite)
class AttributSecuriteAdmin(admin.ModelAdmin):
    list_display = [
        'actif', 'type_attribut', 'cout_compromission_formatted', 
        'risque_financier_display', 'ratio_risque_display', 'niveau_alerte_display', 
        'priorite', 'menaces_count'
    ]
    list_filter = ['type_attribut', 'priorite', 'actif__architecture']
    search_fields = ['actif__nom', 'type_attribut']
    ordering = ['actif', 'type_attribut']
    inlines = [AttributMenaceInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('actif', 'type_attribut', 'priorite')
        }),
        ('Analyse financière', {
            'fields': ('cout_compromission',),
            'description': 'Coût financier estimé si cet attribut était compromis'
        }),
    )
    
    def cout_compromission_formatted(self, obj):
        return '{:,.2f} $'.format(float(obj.cout_compromission))
    cout_compromission_formatted.short_description = 'Coût Compromission'
    
    def risque_financier_display(self, obj):
        risque = obj.risque_financier_attribut
        return '{:,.2f} $'.format(risque)
    risque_financier_display.short_description = 'Risque Calculé'
    
    def ratio_risque_display(self, obj):
        ratio = obj.ratio_risque_cout
        if ratio >= 1.0:
            color = 'darkred'
        elif ratio >= 0.7:
            color = 'red'
        elif ratio >= 0.4:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}</span>',
            color, ratio
        )
    ratio_risque_display.short_description = 'Ratio R/C'
    
    def niveau_alerte_display(self, obj):
        niveau = obj.niveau_alerte
        
        colors = {
            'FAIBLE': 'green',
            'MOYEN': 'orange', 
            'ELEVE': 'red',
            'CRITIQUE': 'darkred'
        }
        color = colors.get(niveau, 'black')
        text_color = 'white' if niveau in ['ELEVE', 'CRITIQUE'] else color
        
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 2px 6px; border-radius: 3px; background-color: {};">{}</span>',
            text_color, color, niveau
        )
    niveau_alerte_display.short_description = 'Niveau Alerte'
    
    def menaces_count(self, obj):
        return obj.menaces.count()
    menaces_count.short_description = 'Nb Menaces'


# ============================================================================
# ADMIN POUR MENACES
# ============================================================================

class MenaceMesureInline(admin.TabularInline):
    """Inline pour afficher les mesures de contrôle associées à la menace"""
    model = MenaceMesure
    extra = 0
    fields = ['mesure_controle', 'efficacite', 'statut_conformite', 'commentaires']
    raw_id_fields = ['mesure_controle']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "mesure_controle":
            kwargs["queryset"] = MesureDeControle.objects.select_related('technique')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Menace)
class MenaceAdmin(admin.ModelAdmin):
    list_display = [
        'nom', 'type_menace', 'severite', 'attributs_count', 
        'mesures_count', 'impact_financier_total', 'created_at'
    ]
    list_filter = ['type_menace', 'severite']
    search_fields = ['nom', 'description']
    ordering = ['nom']
    inlines = [MenaceMesureInline]
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('nom', 'description', 'type_menace', 'severite')
        }),
        ('Contexte', {
            'fields': ('attribut_securite_principal',),
            'description': 'Attribut de sécurité principal associé à cette menace'
        }),
    )
    
    def attributs_count(self, obj):
        return obj.attributs_impactes.count()
    attributs_count.short_description = 'Nb Attributs'
    
    def mesures_count(self, obj):
        return obj.mesures_controle.count()
    mesures_count.short_description = 'Nb Mesures'
    
    def impact_financier_total(self, obj):
        total = sum(attr_menace.risque_financier for attr_menace in obj.attributs_impactes.all())
        return '{:,.2f} $'.format(total)
    impact_financier_total.short_description = 'Impact Financier Total'


# ============================================================================
# ADMIN POUR ATTRIBUT-MENACE
# ============================================================================

@admin.register(AttributMenace)
class AttributMenaceAdmin(admin.ModelAdmin):
    list_display = [
        'attribut_securite', 'menace', 'probabilite', 'impact', 
        'niveau_risque_display', 'cout_impact_formatted', 'risque_financier_display'
    ]
    list_filter = ['menace__severite', 'attribut_securite__type_attribut', 'attribut_securite__actif__architecture']
    ordering = ['-probabilite']
    raw_id_fields = ['attribut_securite', 'menace']
    
    fieldsets = (
        ('Association', {
            'fields': ('attribut_securite', 'menace')
        }),
        ('Évaluation du risque', {
            'fields': ('probabilite', 'impact', 'cout_impact')
        }),
    )
    
    def niveau_risque_display(self, obj):
        risk_level = obj.niveau_risque
        color = 'red' if risk_level > 75 else 'orange' if risk_level > 50 else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}</span>',
            color, risk_level
        )
    niveau_risque_display.short_description = 'Niveau Risque'
    
    def cout_impact_formatted(self, obj):
        return '{:,.2f} $'.format(obj.cout_impact)
    cout_impact_formatted.short_description = 'Coût Impact'
    
    def risque_financier_display(self, obj):
        return '{:,.2f} $'.format(obj.risque_financier)
    risque_financier_display.short_description = 'Risque Financier'


# ============================================================================
# ADMIN POUR MENACE-MESURE (NOUVEAU)
# ============================================================================

@admin.register(MenaceMesure)
class MenaceMesureAdmin(admin.ModelAdmin):
    list_display = [
        'menace', 'mesure_controle', 'technique_display', 'efficacite', 
        'statut_conformite', 'created_at'
    ]
    list_filter = ['statut_conformite', 'menace__severite', 'mesure_controle__nature_mesure']
    search_fields = ['menace__nom', 'mesure_controle__nom', 'mesure_controle__mesure_code']
    ordering = ['menace', 'mesure_controle']
    raw_id_fields = ['menace', 'mesure_controle']
    
    fieldsets = (
        ('Association', {
            'fields': ('menace', 'mesure_controle')
        }),
        ('Efficacité et Conformité', {
            'fields': ('efficacite', 'statut_conformite')
        }),
        ('Notes', {
            'fields': ('commentaires',)
        }),
    )
    
    def technique_display(self, obj):
        return f"{obj.mesure_controle.technique.technique_code} - {obj.mesure_controle.technique.nom[:40]}"
    technique_display.short_description = 'Technique'


# ============================================================================
# ADMIN POUR TECHNIQUES
# ============================================================================

class MesureDeControleInline(admin.TabularInline):
    model = MesureDeControle
    extra = 0
    fields = [
        'mesure_code', 'nom', 'nature_mesure', 'efficacite', 
        'cout_mise_en_oeuvre', 'cout_maintenance_annuel', 
        'duree_implementation', 'cout_total_3_ans_display'
    ]
    readonly_fields = ['cout_total_3_ans_display']
    
    def cout_total_3_ans_display(self, obj):
        if obj.pk:
            return '{:,.2f} $'.format(obj.cout_total_3_ans)
        return "N/A"
    cout_total_3_ans_display.short_description = 'Coût Total 3 ans'


@admin.register(Technique)
class TechniqueAdmin(admin.ModelAdmin):
    list_display = [
        'technique_code', 'nom', 'type_technique', 'complexite', 
        'famille', 'priorite', 'mesures_count', 'cout_moyen'
    ]
    list_filter = ['type_technique', 'complexite', 'famille', 'priorite']
    search_fields = ['technique_code', 'nom', 'description']
    ordering = ['technique_code']
    inlines = [MesureDeControleInline]
    
    fieldsets = (
        ('Informations de la technique', {
            'fields': ('technique_code', 'nom', 'description', 'type_technique', 'complexite')
        }),
        ('Classification', {
            'fields': ('famille', 'priorite'),
            'description': 'Famille et priorité de la technique'
        }),
    )
    
    def mesures_count(self, obj):
        return obj.mesures_controle.count()
    mesures_count.short_description = 'Nb Mesures'
    
    def cout_moyen(self, obj):
        mesures = obj.mesures_controle.all()
        if mesures:
            total_cout = sum(mesure.cout_mise_en_oeuvre for mesure in mesures)
            return '{:,.2f} $'.format(total_cout / len(mesures))
        return "N/A"
    cout_moyen.short_description = 'Coût Moyen'


# ============================================================================
# ADMIN POUR MESURES DE CONTRÔLE
# ============================================================================

class ImplementationMesureInline(admin.TabularInline):
    model = ImplementationMesure
    extra = 0
    fields = ['attribut_menace', 'statut', 'pourcentage_avancement', 'responsable', 'date_fin_prevue']
    raw_id_fields = ['attribut_menace', 'responsable']


@admin.register(MesureDeControle)
class MesureDeControleAdmin(admin.ModelAdmin):
    list_display = [
        'mesure_code', 'nom', 'technique_display', 'nature_mesure', 'efficacite', 
        'cout_mise_en_oeuvre_formatted', 'cout_maintenance_formatted', 
        'duree_implementation', 'menaces_count', 'implementations_count'
    ]
    list_filter = ['nature_mesure', 'technique__type_technique', 'technique__complexite']
    search_fields = ['mesure_code', 'nom', 'description', 'technique__nom', 'technique__technique_code']
    ordering = ['mesure_code']
    inlines = [ImplementationMesureInline]
    raw_id_fields = ['technique']
    
    fieldsets = (
        ('Technique associée', {
            'fields': ('technique',)
        }),
        ('Informations Générales', {
            'fields': ('mesure_code', 'nom', 'description', 'nature_mesure')
        }),
        ('Coûts et Efficacité', {
            'fields': ('cout_mise_en_oeuvre', 'cout_maintenance_annuel', 'efficacite')
        }),
        ('Implémentation', {
            'fields': ('duree_implementation', 'ressources_necessaires')
        }),
    )
    
    def technique_display(self, obj):
        return f"{obj.technique.technique_code} - {obj.technique.nom[:40]}"
    technique_display.short_description = 'Technique'
    
    def cout_mise_en_oeuvre_formatted(self, obj):
        return '{:,.2f} $'.format(obj.cout_mise_en_oeuvre)
    cout_mise_en_oeuvre_formatted.short_description = 'Coût Mise en Œuvre'
    
    def cout_maintenance_formatted(self, obj):
        return '{:,.2f} $'.format(obj.cout_maintenance_annuel)
    cout_maintenance_formatted.short_description = 'Coût Maintenance/an'
    
    def menaces_count(self, obj):
        return obj.menaces_traitees.count()
    menaces_count.short_description = 'Nb Menaces'
    
    def implementations_count(self, obj):
        return obj.implementations.count()
    implementations_count.short_description = 'Nb Implémentations'


# ============================================================================
# ADMIN POUR IMPLÉMENTATIONS
# ============================================================================

@admin.register(ImplementationMesure)
class ImplementationMesureAdmin(admin.ModelAdmin):
    list_display = [
        'mesure_controle_display', 'attribut_menace_display', 'statut', 
        'pourcentage_avancement', 'responsable', 'date_fin_prevue', 'risque_residuel_display'
    ]
    list_filter = ['statut', 'responsable', 'mesure_controle__nature_mesure']
    date_hierarchy = 'date_fin_prevue'
    ordering = ['-created_at']
    raw_id_fields = ['attribut_menace', 'mesure_controle', 'responsable']
    
    fieldsets = (
        ('Association', {
            'fields': ('attribut_menace', 'mesure_controle')
        }),
        ('Statut et Avancement', {
            'fields': ('statut', 'pourcentage_avancement')
        }),
        ('Planification', {
            'fields': ('date_debut_prevue', 'date_fin_prevue', 'date_implementation')
        }),
        ('Responsabilités', {
            'fields': ('responsable', 'equipe')
        }),
        ('Suivi', {
            'fields': ('commentaires', 'obstacles')
        }),
    )
    
    def mesure_controle_display(self, obj):
        nom = obj.mesure_controle.nom
        return nom[:40] + '...' if len(nom) > 40 else nom
    mesure_controle_display.short_description = 'Mesure de Contrôle'
    
    def attribut_menace_display(self, obj):
        actif_nom = obj.attribut_menace.attribut_securite.actif.nom
        menace_nom = obj.attribut_menace.menace.nom[:20]
        return '{} - {}...'.format(actif_nom, menace_nom)
    attribut_menace_display.short_description = 'Risque Traité'
    
    def risque_residuel_display(self, obj):
        risk_level = obj.risque_residuel
        color = 'red' if risk_level > 75 else 'orange' if risk_level > 50 else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}</span>',
            color, risk_level
        )
    risque_residuel_display.short_description = 'Risque Résiduel'


# ============================================================================
# ADMIN POUR LOGS
# ============================================================================

@admin.register(LogActivite)
class LogActiviteAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'action', 'objet_type', 'objet_id', 'created_at']
    list_filter = ['action', 'objet_type', 'utilisateur']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
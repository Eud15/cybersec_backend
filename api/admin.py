# api/admin.py - Version complète corrigée
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    TypeActif, Architecture, Actif, AttributSecurite, Menace, AttributMenace,
    ControleNIST, MenaceControle, Technique, MesureDeControle, 
    ImplementationMesure, LogActivite
)

@admin.register(TypeActif)
class TypeActifAdmin(admin.ModelAdmin):
    list_display = ['nom', 'description', 'actifs_count', 'created_at']
    search_fields = ['nom', 'description']
    ordering = ['nom']
    
    def actifs_count(self, obj):
        return obj.actifs.count()
    actifs_count.short_description = 'Nb Actifs'

# Inline pour les actifs dans une architecture
class ActifInline(admin.TabularInline):
    model = Actif
    extra = 0
    fields = ['nom', 'type_actif', 'cout', 'criticite', 'proprietaire']
    readonly_fields = ['nom']

@admin.register(Architecture)
class ArchitectureAdmin(admin.ModelAdmin):
    list_display = ['nom', 'risque_tolere_formatted', 'actifs_count', 'risque_financier_total_display', 'tolerance_status', 'created_at']
    search_fields = ['nom', 'description']
    inlines = [ActifInline]
    ordering = ['nom']
    
    def risque_tolere_formatted(self, obj):
        return '{:,.2f} €'.format(obj.risque_tolere)
    risque_tolere_formatted.short_description = 'Tolérance Risque'
    
    def actifs_count(self, obj):
        return obj.actifs.count()
    actifs_count.short_description = 'Nb Actifs'
    
    def risque_financier_total_display(self, obj):
        total = obj.risque_financier_total
        return '{:,.2f} €'.format(total)
    risque_financier_total_display.short_description = 'Risque Total'
    
    def tolerance_status(self, obj):
        if obj.risque_depasse_tolerance:
            return format_html(
                '<span style="color: red; font-weight: bold;">DÉPASSÉ ({:.1f}%)</span>',
                obj.pourcentage_tolerance_utilise
            )
        else:
            color = 'orange' if obj.pourcentage_tolerance_utilise > 80 else 'green'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, obj.pourcentage_tolerance_utilise
            )
    tolerance_status.short_description = 'Statut Tolérance'

# Inline pour les attributs de sécurité dans un actif (CORRIGÉ)
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
                color, 
                niveau
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
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, 
                '{:.2f}'.format(ratio)
            )
        return "N/A"
    ratio_display.short_description = 'Ratio'
@admin.register(Actif)
class ActifAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_actif', 'architecture', 'cout_formatted', 'criticite', 'proprietaire', 'attributs_count', 'risque_total']
    list_filter = ['type_actif', 'architecture', 'criticite', 'proprietaire']
    search_fields = ['nom', 'description']
    ordering = ['architecture', 'nom']
    inlines = [AttributSecuriteInline]
    
    def cout_formatted(self, obj):
        return '{:,.2f} €'.format(obj.cout)
    cout_formatted.short_description = 'Coût'
    
    def attributs_count(self, obj):
        return obj.attributs_securite.count()
    attributs_count.short_description = 'Nb Attributs'
    
    def risque_total(self, obj):
        total = 0
        for attr_secu in obj.attributs_securite.all():
            total += attr_secu.risque_financier_attribut
        return '{:,.2f} €'.format(total)
    risque_total.short_description = 'Risque Total'

# Inline pour les associations attribut-menace
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
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, 
                '{:.2f}'.format(risk_level)
            )
        return "N/A"
    niveau_risque_display.short_description = 'Niveau Risque'
    
    def risque_financier_display(self, obj):
        if obj.pk:
            return '{:,.2f} €'.format(obj.risque_financier)
        return "N/A"
    risque_financier_display.short_description = 'Risque €'
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
        return '{:,.2f} €'.format(float(obj.cout_compromission))
    cout_compromission_formatted.short_description = 'Coût Compromission'
    
    def risque_financier_display(self, obj):
        risque = obj.risque_financier_attribut
        return '{:,.2f} €'.format(risque)
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
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, 
            '{:.2f}'.format(ratio)
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
            text_color,
            color,
            niveau
        )
    niveau_alerte_display.short_description = 'Niveau Alerte'
    
    def menaces_count(self, obj):
        return obj.menaces.count()
    menaces_count.short_description = 'Nb Menaces'

# Inline pour les associations menace-contrôle
class MenaceControleInline(admin.TabularInline):
    model = MenaceControle
    extra = 0
    fields = ['controle_nist', 'efficacite', 'statut_conformite', 'commentaires']

@admin.register(Menace)
class MenaceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_menace', 'severite', 'attributs_count', 'controles_count', 'impact_financier_total', 'created_at']
    list_filter = ['type_menace', 'severite']
    search_fields = ['nom', 'description']
    ordering = ['nom']
    inlines = [MenaceControleInline]
    
    def attributs_count(self, obj):
        return obj.attributs_impactes.count()
    attributs_count.short_description = 'Nb Attributs'
    
    def controles_count(self, obj):
        return obj.controles_nist.count()
    controles_count.short_description = 'Nb Contrôles'
    
    def impact_financier_total(self, obj):
        total = sum(attr_menace.risque_financier for attr_menace in obj.attributs_impactes.all())
        return '{:,.2f} €'.format(total)
    impact_financier_total.short_description = 'Impact Financier Total'

@admin.register(AttributMenace)
class AttributMenaceAdmin(admin.ModelAdmin):
    list_display = [
        'attribut_securite', 'menace', 'probabilite', 'impact', 
        'niveau_risque_display', 'cout_impact_formatted', 'risque_financier_display'
    ]
    list_filter = ['menace__severite', 'attribut_securite__type_attribut', 'attribut_securite__actif__architecture']
    ordering = ['-probabilite']
    raw_id_fields = ['attribut_securite', 'menace']
    
    def niveau_risque_display(self, obj):
        risk_level = obj.niveau_risque
        color = 'red' if risk_level > 75 else 'orange' if risk_level > 50 else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}</span>',
            color, risk_level
        )
    niveau_risque_display.short_description = 'Niveau Risque'
    
    def cout_impact_formatted(self, obj):
        return '{:,.2f} €'.format(obj.cout_impact)
    cout_impact_formatted.short_description = 'Coût Impact'
    
    def risque_financier_display(self, obj):
        return '{:,.2f} €'.format(obj.risque_financier)
    risque_financier_display.short_description = 'Risque Financier'

# Inline pour les techniques dans un contrôle NIST
class TechniqueInline(admin.TabularInline):
    model = Technique
    extra = 0
    fields = ['nom', 'type_technique', 'complexite', 'mesures_count']
    readonly_fields = ['mesures_count']
    
    def mesures_count(self, obj):
        if obj.pk:
            return obj.mesures_controle.count()
        return 0
    mesures_count.short_description = 'Nb Mesures'

@admin.register(ControleNIST)
class ControleNISTAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'famille', 'priorite', 'techniques_count', 'menaces_count', 'created_at']
    list_filter = ['famille', 'priorite']
    search_fields = ['code', 'nom', 'description']
    ordering = ['code']
    inlines = [TechniqueInline]
    
    def techniques_count(self, obj):
        return obj.techniques.count()
    techniques_count.short_description = 'Nb Techniques'
    
    def menaces_count(self, obj):
        return obj.menaces_traitees.count()
    menaces_count.short_description = 'Nb Menaces'

@admin.register(MenaceControle)
class MenaceControleAdmin(admin.ModelAdmin):
    list_display = ['menace', 'controle_nist', 'efficacite', 'statut_conformite', 'techniques_count']
    list_filter = ['statut_conformite', 'controle_nist__famille', 'controle_nist__priorite']
    ordering = ['menace', 'controle_nist']
    raw_id_fields = ['menace', 'controle_nist']
    
    def techniques_count(self, obj):
        return obj.controle_nist.techniques.count()
    techniques_count.short_description = 'Nb Techniques'

# Inline pour les mesures de contrôle dans une technique
class MesureDeControleInline(admin.TabularInline):
    model = MesureDeControle
    extra = 0
    fields = [
        'nom', 'nature_mesure', 'efficacite', 
        'cout_mise_en_oeuvre', 'cout_maintenance_annuel', 
        'duree_implementation', 'cout_total_3_ans_display'
    ]
    readonly_fields = ['cout_total_3_ans_display']
    
    def cout_total_3_ans_display(self, obj):
        if obj.pk:
            return '{:,.2f} €'.format(obj.cout_total_3_ans)
        return "N/A"
    cout_total_3_ans_display.short_description = 'Coût Total 3 ans'

@admin.register(Technique)
class TechniqueAdmin(admin.ModelAdmin):
    list_display = ['nom', 'controle_nist_display', 'type_technique', 'complexite', 'mesures_count', 'cout_moyen']
    list_filter = ['type_technique', 'complexite', 'controle_nist__famille']
    search_fields = ['nom', 'description', 'controle_nist__code', 'controle_nist__nom']
    ordering = ['controle_nist', 'nom']
    inlines = [MesureDeControleInline]
    raw_id_fields = ['controle_nist']
    
    def controle_nist_display(self, obj):
        return '{} - {}...'.format(obj.controle_nist.code, obj.controle_nist.nom[:30])
    controle_nist_display.short_description = 'Contrôle NIST'
    
    def mesures_count(self, obj):
        return obj.mesures_controle.count()
    mesures_count.short_description = 'Nb Mesures'
    
    def cout_moyen(self, obj):
        mesures = obj.mesures_controle.all()
        if mesures:
            total_cout = sum(mesure.cout_mise_en_oeuvre for mesure in mesures)
            return '{:,.2f} €'.format(total_cout / len(mesures))
        return "N/A"
    cout_moyen.short_description = 'Coût Moyen'

# Inline pour les implémentations dans une mesure de contrôle
class ImplementationMesureInline(admin.TabularInline):
    model = ImplementationMesure
    extra = 0
    fields = ['attribut_menace', 'statut', 'pourcentage_avancement', 'responsable', 'date_fin_prevue']
    readonly_fields = ['attribut_menace']

@admin.register(MesureDeControle)
class MesureDeControleAdmin(admin.ModelAdmin):
    list_display = [
        'nom', 'technique_display', 'nature_mesure', 'efficacite', 
        'cout_mise_en_oeuvre_formatted', 'cout_maintenance_formatted', 
        'duree_implementation', 'implementations_count'
    ]
    list_filter = ['nature_mesure', 'technique__type_technique', 'technique__controle_nist__famille']
    search_fields = ['nom', 'description', 'technique__nom', 'technique__controle_nist__code']
    ordering = ['technique', 'nom']
    inlines = [ImplementationMesureInline]
    raw_id_fields = ['technique']
    
    fieldsets = (
        ('Informations Générales', {
            'fields': ('technique', 'nom', 'description', 'nature_mesure')
        }),
        ('Coûts et Efficacité', {
            'fields': ('cout_mise_en_oeuvre', 'cout_maintenance_annuel', 'efficacite')
        }),
        ('Implémentation', {
            'fields': ('duree_implementation', 'ressources_necessaires')
        }),
    )
    
    def technique_display(self, obj):
        return '{} - {}...'.format(obj.technique.controle_nist.code, obj.technique.nom[:30])
    technique_display.short_description = 'Technique'
    
    def cout_mise_en_oeuvre_formatted(self, obj):
        return '{:,.2f} €'.format(obj.cout_mise_en_oeuvre)
    cout_mise_en_oeuvre_formatted.short_description = 'Coût Mise en Œuvre'
    
    def cout_maintenance_formatted(self, obj):
        return '{:,.2f} €'.format(obj.cout_maintenance_annuel)
    cout_maintenance_formatted.short_description = 'Coût Maintenance/an'
    
    def implementations_count(self, obj):
        return obj.implementations.count()
    implementations_count.short_description = 'Nb Implémentations'

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
        return '{}...'.format(obj.mesure_controle.nom[:40])
    mesure_controle_display.short_description = 'Mesure de Contrôle'
    
    def attribut_menace_display(self, obj):
        return '{} - {}...'.format(obj.attribut_menace.attribut_securite.actif.nom, obj.attribut_menace.menace.nom[:20])
    attribut_menace_display.short_description = 'Risque Traité'
    
    def risque_residuel_display(self, obj):
        risk_level = obj.risque_residuel
        color = 'red' if risk_level > 75 else 'orange' if risk_level > 50 else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}</span>',
            color, risk_level
        )
    risque_residuel_display.short_description = 'Risque Résiduel'

@admin.register(LogActivite)
class LogActiviteAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'action', 'objet_type', 'objet_id', 'created_at']
    list_filter = ['action', 'objet_type', 'utilisateur']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        return False  # Les logs ne doivent pas être créés manuellement
    
    def has_change_permission(self, request, obj=None):
        return False  # Les logs ne doivent pas être modifiés
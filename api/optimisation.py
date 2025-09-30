#import pandas as pd
import pyomo.environ as pyo

# Chargement des données Excel
#df = pd.read_excel('security_data_with_impact.xlsx')

# Chemin vers le solveur BONMIN (assure-toi que ce chemin est correct)
# solver_path = '/usr/local/bin/bonmin'
solver_path = r"C:\BONMIN\bonmin.exe"
solver = pyo.SolverFactory('bonmin', executable=solver_path)

import pymysql

conn = pymysql.connect(
    host="localhost",
    user="root",
    password="Hayye1-Samir2",
    database="test_db"
)
cursor = conn.cursor()

pActif='ARCH13'

lstActif="""SELECT Cod_actif, Lib_actif, Cout_actif, Cod_tp_actif, Cod_architecture FROM test_db.actif
WHERE Cod_architecture=%s
"""

lstAttribut="""SELECT Cod_attribut_securite FROM test_db.associer
Where Cod_actif=%s
Group by Cod_attribut_securite
"""

lstMesureAttribut="""SELECT m.Cod_mesuredecontrole,me.CoutMiseEnOuevre
FROM test_db.associer AS a
INNER JOIN test_db.mitiger AS m ON a.Cod_menace = m.Cod_menace
INNER JOIN test_db.mesuredecontrole AS me ON m.Cod_mesuredecontrole = me.Cod_mesuredecontrole
WHERE a.Cod_actif=%s AND a.Cod_attribut_securite=%s  
"""


lstMesureAttributMenace="""SELECT a.Cod_attribut_securite,m.Cod_menace, me.CoutMiseEnOuevre, a.probabilite,  
    m.Cod_mesuredecontrole, m.natureMesure, a.coutImpact, a.Cod_menace, a.IDASSOC, a.Cod_actif,  
    m.efficacite,  me.Lib_mesuredecontrole
FROM test_db.associer AS a
INNER JOIN test_db.mitiger AS m ON a.Cod_menace = m.Cod_menace
INNER JOIN test_db.mesuredecontrole AS me ON m.Cod_mesuredecontrole = me.Cod_mesuredecontrole
WHERE a.Cod_actif=%s AND a.Cod_attribut_securite=%s AND m.Cod_menace =%s
"""

lstImpactMemaceAttribut="""SELECT Cod_attribut_securite, coutImpact, probabilite, Cod_menace, IDASSOC, Cod_actif
FROM test_db.associer
WHERE Cod_actif=%s AND Cod_attribut_securite=%s
"""

lstATtributSec=""" SELECT Cod_attribut_securite, Lib_attribut_securite, ImpactAttribut
FROM test_db.attribut_securite
WHERE Cod_attribut_securite=%s
"""

selected_measures_final = []

print("Architecture :", pActif)

cursor.execute(lstActif,(pActif,))
tbActif=cursor.fetchall()
for tA in tbActif: # 1- Traitement d'un Actif
    print("    Actif :", tA)
    cursor.execute(lstAttribut, (tA[0],))
    tbAttribut = cursor.fetchall()

    print (tbAttribut)
    for tAT in tbAttribut: # 1- Traitement des attribut de sécurité pour chaque actif
        print("        Attribut :", tAT[0])

        # On va chercher les mesures en faisant la jointure sur les menaces liées à l'attribut de sécurité
        cursor.execute(lstMesureAttribut, (tA[0],tAT[0],))
        tbMesureAttribut = cursor.fetchall()
        lstMesure = [row[0] for row in tbMesureAttribut]

        if len(lstMesure)<= 0:
            break

        model = pyo.ConcreteModel()  #
        model.M = pyo.Set(initialize=lstMesure)
        model.x = pyo.Var(model.M, domain=pyo.Boolean)

        model.objective = pyo.Objective( #  Fait la somme du cout de l'implémentation pour les mesures choisies
            #expr=sum(lg[2] for lg in tbMesureAttribut if (model.x[lg[0]]==True) for lg[0] in model.M),
            expr=sum(lg[1] * model.x[lg[0]] for lg in tbMesureAttribut),
            sense=pyo.minimize
        )

        model.risk_constraint = pyo.ConstraintList()

        # Cherche le cout de l'impact de L'attribut de sécurité
        cursor.execute(lstATtributSec, (tAT[0],))
        tbATtributSec=cursor.fetchall()
        impact = tbATtributSec [0][2]
        print("        impact attribut :", impact)

        proba_residuelles = []


# Récupérer les menaces
        cursor.execute(lstImpactMemaceAttribut, (tA[0], tAT[0],))
        tbImpactMemaceAttribut = cursor.fetchall()
        lstMenace = [row[3] for row in tbImpactMemaceAttribut]
        lstMenaceuniq=list(set(lstMenace))

        print(lstMenaceuniq)
        for tATMen in lstMenaceuniq :
            #print("                  Meance :", tATMen)
            cursor.execute(lstMesureAttributMenace, (tA[0], tAT[0],tATMen,))
            tbMesureAttributMenace = cursor.fetchall()
            lstMes = [row[4] for row in tbMesureAttributMenace]
            lstMesuniq = list(set(lstMes))

            for z in tbMesureAttributMenace :
                initial_proba = z[3]  # Tmes[3] Probabilité de la menace
            print("                          Probabilite :", initial_proba)
            proba_res = initial_proba

            # Récupérer de l,efficacité et de la nature des mesures de controles
            for Tmes in tbMesureAttributMenace :
                # print("                          Mesure :", Tmes[4],Tmes[3], Tmes[5])
                natureMes = Tmes[5]

                if Tmes[5] in ['IS','IP']:
                    proba_res = proba_res * (1- Tmes[10])* model.x[Tmes[4]]
                elif Tmes[5] == 'RA':
                    var_aux_ra = pyo.Var(bounds=(0, 1)) #  Creation de la variable var_aux_ra qui peut prendre des valeurs entre 0 et 1
                    model.add_component(f'RA_aux_{Tmes}', var_aux_ra) #  Ajout de la variable dans le modèle
                    model.risk_constraint.add(var_aux_ra >= Tmes[10] * model.x[Tmes[4]]) # p[10] renvoie l'efficacité , p[4] code de la mesure de controle
                    proba_res = proba_res * (1 - var_aux_ra)

                elif Tmes[5] == 'RC':
                    var_aux_rc = pyo.Var(bounds=(0, 1)) #  Creation de la variable var_aux_ra qui peut prendre des valeurs entre 0 et 1
                    model.add_component(f'RC_aux_{Tmes}', var_aux_rc) #  Ajout de la variable dans le modèle
                    model.risk_constraint.add(var_aux_rc <= Tmes[10] * model.x[Tmes[4]] + (1-model.x[Tmes[4]])) # p[10] renvoie l'efficacité, p[4] code de la mesure de controle
                    proba_res = proba_res * (1 - var_aux_rc)

            proba_residuelles.append(proba_res)

        # Seuil local (ajustable selon tes besoins)
        seuil_local = 50  # à ajuster

        if len (proba_residuelles)> 0:
            risque_local = (1 - pyo.prod(1 - p for p in proba_residuelles)) * impact
            model.risk_constraint.add(risque_local <= seuil_local)
        else :
            model.risk_constraint.add(pyo.Constraint.Feasible)

        # Vérifie que lstMes n’est pas vide
        if lstMesuniq:
            # Extraire seulement les identifiants qui sont bien dans model.M
            valid_keys = [m for m in lstMesuniq if m in model.M]
            if valid_keys:
                model.risk_constraint.add(sum(model.x[m] for m in valid_keys) >= 1)
            else:
                # Aucun identifiant valide → contrainte triviale
                model.risk_constraint.add(pyo.Constraint.Feasible)
        else:
            # Liste vide → contrainte triviale
            model.risk_constraint.add(pyo.Constraint.Feasible)

        print("             Contenu de model.M :", list(model.M))


        result = solver.solve(model, tee=False)

        # Vérification de la faisabilité
        if result.solver.termination_condition == pyo.TerminationCondition.optimal:
            selected = [i for i in model.M if pyo.value(model.x[i]) > 0.5]
            selected_measures_final.extend(selected)
            print(selected)

        else:
            print(f"            Pas de solution trouvée pour {tA} - {tAT}, revoir contraintes.")

print(len(selected_measures_final))

cursor.close()
conn.close()
# Stocker les résultats finaux ici
selected_measures_final = []
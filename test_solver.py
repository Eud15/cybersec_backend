#!/usr/bin/env python
"""
Script de test pour vérifier la disponibilité des solveurs Pyomo
"""
import sys

def test_pyomo_import():
    """Teste l'importation de Pyomo"""
    print("=== Test d'importation de Pyomo ===")
    try:
        import pyomo.environ as pyo
        print("✓ Pyomo importé avec succès")
        print(f"  Version : {pyo.__version__ if hasattr(pyo, '__version__') else 'Non disponible'}")
        return True
    except ImportError as e:
        print(f"✗ Erreur d'importation de Pyomo : {e}")
        print("\nPour installer Pyomo : pip install pyomo")
        return False

def test_solvers():
    """Teste la disponibilité des solveurs"""
    try:
        import pyomo.environ as pyo
    except ImportError:
        print("\nPyomo n'est pas installé. Impossible de tester les solveurs.")
        return []
    
    print("\n=== Test des solveurs disponibles ===\n")
    
    # Liste des solveurs à tester
    solvers_to_test = [
        ('glpk', 'GLPK - Solveur linéaire open source'),
        ('cbc', 'CBC - Solveur linéaire open source'),
        ('ipopt', 'IPOPT - Solveur non-linéaire'),
        ('bonmin', 'BONMIN - Solveur mixte entier non-linéaire'),
        ('gurobi', 'Gurobi - Solveur commercial'),
        ('cplex', 'CPLEX - Solveur commercial'),
    ]
    
    available_solvers = []
    unavailable_solvers = []
    
    for solver_name, description in solvers_to_test:
        try:
            solver = pyo.SolverFactory(solver_name)
            if solver.available():
                print(f"✓ {solver_name:10} : DISPONIBLE")
                print(f"             {description}")
                available_solvers.append(solver_name)
            else:
                print(f"✗ {solver_name:10} : Installé mais non accessible")
                print(f"             {description}")
                unavailable_solvers.append(solver_name)
        except Exception as e:
            print(f"✗ {solver_name:10} : Non installé")
            print(f"             {description}")
            unavailable_solvers.append(solver_name)
        print()
    
    print("="*60)
    print(f"\nRésumé : {len(available_solvers)} solveur(s) disponible(s) sur {len(solvers_to_test)}")
    
    if available_solvers:
        print(f"\nSolveurs disponibles : {', '.join(available_solvers)}")
        print(f"Solveur recommandé : {available_solvers[0]}")
    else:
        print("\n⚠️  AUCUN SOLVEUR TROUVÉ")
        print("\nPour installer un solveur (choisissez une option) :")
        print("  1. Via conda (recommandé pour Windows) :")
        print("     conda install -c conda-forge glpk")
        print("\n  2. Via pip :")
        print("     pip install glpk")
        print("\n  3. Téléchargement manuel (GLPK pour Windows) :")
        print("     https://sourceforge.net/projects/winglpk/")
    
    return available_solvers

def test_simple_optimization():
    """Teste une optimisation simple"""
    try:
        import pyomo.environ as pyo
    except ImportError:
        return False
    
    print("\n=== Test d'optimisation simple ===\n")
    
    # Trouver un solveur disponible
    for solver_name in ['glpk', 'cbc', 'ipopt']:
        try:
            solver = pyo.SolverFactory(solver_name)
            if solver.available():
                print(f"Utilisation du solveur : {solver_name}\n")
                
                # Créer un modèle simple
                model = pyo.ConcreteModel()
                model.x = pyo.Var([1, 2], domain=pyo.NonNegativeReals)
                model.obj = pyo.Objective(expr=2*model.x[1] + 3*model.x[2])
                model.constraint = pyo.Constraint(expr=model.x[1] + model.x[2] >= 1)
                
                # Résoudre
                try:
                    result = solver.solve(model)
                    
                    if result.solver.termination_condition == pyo.TerminationCondition.optimal:
                        print("✓ Optimisation réussie !")
                        print(f"  Solution : x[1]={pyo.value(model.x[1]):.2f}, x[2]={pyo.value(model.x[2]):.2f}")
                        print(f"  Valeur objectif : {pyo.value(model.obj):.2f}")
                        return True
                    else:
                        print(f"✗ Optimisation échouée : {result.solver.termination_condition}")
                        return False
                except Exception as e:
                    print(f"✗ Erreur lors de la résolution : {e}")
                    return False
        except Exception as e:
            continue
    
    print("✗ Aucun solveur disponible pour tester l'optimisation")
    return False

def print_recommendations():
    """Affiche des recommandations d'installation"""
    print("\n" + "="*60)
    print("\n💡 RECOMMANDATIONS POUR WINDOWS\n")
    print("Installation la plus simple (avec conda) :")
    print("  1. Installer Miniconda : https://docs.conda.io/en/latest/miniconda.html")
    print("  2. conda install -c conda-forge glpk")
    print("  3. python test_solver.py  # Vérifier l'installation")
    print("\nAlternative (sans conda) :")
    print("  1. pip install glpk")
    print("  2. Si ça ne fonctionne pas, télécharger GLPK pour Windows")
    print("  3. https://sourceforge.net/projects/winglpk/")
    print("  4. Extraire dans C:\\glpk et ajouter au PATH")
    print("\n" + "="*60)

def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print(" TEST DE CONFIGURATION PYOMO POUR DJANGO")
    print("="*60 + "\n")
    
    # Test 1 : Import Pyomo
    if not test_pyomo_import():
        print("\n❌ Impossible de continuer sans Pyomo")
        print("   Installation : pip install pyomo")
        sys.exit(1)
    
    # Test 2 : Solveurs disponibles
    available_solvers = test_solvers()
    
    # Test 3 : Optimisation simple
    if available_solvers:
        test_simple_optimization()
        print("\n" + "="*60)
        print("\n✅ CONFIGURATION OK - Le serveur Django peut utiliser l'optimisation")
        print(f"   Solveur actif : {available_solvers[0]}")
        print("\nVous pouvez maintenant lancer :")
        print("   python manage.py runserver")
    else:
        print("\n" + "="*60)
        print("\n⚠️  CONFIGURATION INCOMPLÈTE")
        print("\nLe serveur Django démarrera MAIS les fonctionnalités")
        print("d'optimisation seront désactivées.")
        print("\nPour activer l'optimisation, installez un solveur.")
        print_recommendations()
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
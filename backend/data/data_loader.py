# ===== backend/data/data_loader.py - AVEC INTÉGRATION PEA =====
from backend.models.database import DatabaseManager
from backend.data.parsers import LBPParser, PretUpParser, BienPreterParser, HomunityParser
from backend.data.pea_parser import PEAParser
import os

class DataLoader:
    """Classe principale pour charger les données des différentes plateformes"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def load_platform_data(self, file_path: str, platform: str, user_id: str) -> bool:
        """Charger les données depuis un fichier de plateforme crowdfunding"""
        
        print(f"📥 Chargement des données {platform.upper()} pour l'utilisateur {user_id}")
        
        # Sélectionner le parser approprié
        if platform.lower() == 'lbp':
            parser = LBPParser(user_id)
        elif platform.lower() == 'pretup':
            parser = PretUpParser(user_id)
        elif platform.lower() == 'bienpreter':
            parser = BienPreterParser(user_id)
        elif platform.lower() == 'homunity':
            parser = HomunityParser(user_id)
        else:
            print(f"❌ Parser non implémenté pour la plateforme: {platform}")
            return False
        
        try:
            # Parser les données
            print(f"🔍 Parsing du fichier: {file_path}")
            investissements, flux_tresorerie = parser.parse(file_path)
            
            print(f"📊 Données parsées: {len(investissements)} investissements, {len(flux_tresorerie)} flux de trésorerie")
            
            # Insérer en base de données
            succes_inv = self.db.insert_investments(investissements)
            succes_cf = self.db.insert_cash_flows(flux_tresorerie)
            
            if succes_inv and succes_cf:
                print(f"✅ Chargement réussi de {platform.upper()}")
                return True
            else:
                print(f"⚠️  Chargement partiel de {platform.upper()}")
                return False
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement des données de {platform}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_pea_data(self, releve_pdf_path: str = None, evaluation_pdf_path: str = None, user_id: str = None) -> bool:
        """
        Charger les données PEA depuis les PDFs Bourse Direct
        
        Args:
            releve_pdf_path: Chemin vers le PDF du relevé de compte
            evaluation_pdf_path: Chemin vers le PDF d'évaluation de portefeuille
            user_id: ID utilisateur
        
        Returns:
            bool: True si succès, False sinon
        """
        
        if not user_id:
            print("❌ User ID requis pour charger les données PEA")
            return False
        
        print(f"🏦 Chargement des données PEA pour l'utilisateur {user_id}")
        
        # Vérifier qu'au moins un fichier est fourni
        if not releve_pdf_path and not evaluation_pdf_path:
            print("❌ Au moins un fichier PDF PEA est requis")
            return False
        
        # Vérifier l'existence des fichiers
        files_to_check = []
        if releve_pdf_path:
            files_to_check.append(('Relevé', releve_pdf_path))
        if evaluation_pdf_path:
            files_to_check.append(('Évaluation', evaluation_pdf_path))
        
        for file_type, file_path in files_to_check:
            if not os.path.exists(file_path):
                print(f"⚠️  Fichier {file_type} PEA non trouvé: {file_path}")
                return False
            else:
                print(f"✅ Fichier {file_type} PEA trouvé: {file_path}")
        
        try:
            # Créer le parser PEA
            parser = PEAParser(user_id)
            
            # Parser les fichiers PDF
            print("🔍 Parsing des fichiers PDF PEA...")
            investissements, flux_tresorerie, positions = parser.parse_pdf_files(
                releve_pdf_path, evaluation_pdf_path
            )
            
            print(f"📊 Données PEA parsées:")
            print(f"  - {len(investissements)} investissements")
            print(f"  - {len(flux_tresorerie)} flux de trésorerie")
            print(f"  - {len(positions)} positions")
            
            # Insérer en base de données
            success_results = []
            
            # Insérer les investissements
            if investissements:
                success_inv = self.db.insert_investments(investissements)
                success_results.append(('investissements', success_inv))
                if success_inv:
                    print(f"✅ {len(investissements)} investissements PEA insérés")
                else:
                    print(f"❌ Échec insertion investissements PEA")
            else:
                print("ℹ️  Aucun investissement PEA à insérer")
                success_results.append(('investissements', True))
            
            # Insérer les flux de trésorerie
            if flux_tresorerie:
                success_cf = self.db.insert_cash_flows(flux_tresorerie)
                success_results.append(('flux_tresorerie', success_cf))
                if success_cf:
                    print(f"✅ {len(flux_tresorerie)} flux de trésorerie PEA insérés")
                else:
                    print(f"❌ Échec insertion flux de trésorerie PEA")
            else:
                print("ℹ️  Aucun flux de trésorerie PEA à insérer")
                success_results.append(('flux_tresorerie', True))
            
            # Insérer les positions (optionnel - nécessite une table portfolio_positions)
            if positions:
                try:
                    success_pos = self.db.insert_portfolio_positions(positions)
                    success_results.append(('positions', success_pos))
                    if success_pos:
                        print(f"✅ {len(positions)} positions PEA insérées")
                    else:
                        print(f"❌ Échec insertion positions PEA")
                except AttributeError:
                    print("ℹ️  Table positions non disponible - ignoré")
                    success_results.append(('positions', True))
            else:
                print("ℹ️  Aucune position PEA à insérer")
                success_results.append(('positions', True))
            
            # Vérifier le succès global
            all_success = all(success for _, success in success_results)
            
            if all_success:
                print("✅ Chargement PEA terminé avec succès")
                return True
            else:
                failed_operations = [op for op, success in success_results if not success]
                print(f"⚠️  Chargement PEA partiel - échecs: {', '.join(failed_operations)}")
                return False
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement PEA: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_all_user_files(self, user_id: str, data_folder: str = "data/raw") -> bool:
        """Charger tous les fichiers depuis le dossier de données utilisateur"""
        
        fichiers_plateformes = {
            'lbp': 'Portefeuille LPB 20250529.xlsx',
            'pretup': 'Portefeuille PretUp 20250529.xlsx',
            'bienpreter': 'Portefeuille BienPreter 20250529.xlsx',
            'homunity': 'Portefeuille Homunity 20250529.xlsx'
        }
        
        succes_count = 0
        
        # Charger les plateformes de crowdfunding
        for plateforme, filename in fichiers_plateformes.items():
            file_path = os.path.join(data_folder, filename)
            if os.path.exists(file_path):
                print(f"\n📂 Traitement de {plateforme.upper()}...")
                if self.load_platform_data(file_path, plateforme, user_id):
                    succes_count += 1
                else:
                    print(f"❌ Échec du chargement de {plateforme}")
            else:
                print(f"⚠️  Fichier non trouvé: {file_path}")
        
        # Charger les données PEA si disponibles
        pea_folder = os.path.join(data_folder, "pea")
        releve_pea = None
        evaluation_pea = None
        
        if os.path.exists(pea_folder):
            # Chercher les fichiers PEA
            for file in os.listdir(pea_folder):
                if file.lower().endswith('.pdf'):
                    if 'releve' in file.lower() or 'compte' in file.lower():
                        releve_pea = os.path.join(pea_folder, file)
                    elif 'evaluation' in file.lower() or 'portefeuille' in file.lower():
                        evaluation_pea = os.path.join(pea_folder, file)
            
            if releve_pea or evaluation_pea:
                print(f"\n🏦 Traitement PEA...")
                if self.load_pea_data(releve_pea, evaluation_pea, user_id):
                    succes_count += 1
                else:
                    print(f"❌ Échec du chargement PEA")
        
        total_platforms = len(fichiers_plateformes) + (1 if (releve_pea or evaluation_pea) else 0)
        print(f"\n📋 Résumé: {succes_count}/{total_platforms} sources chargées avec succès")
        
        return succes_count > 0
    
    def clear_user_data(self, user_id: str) -> bool:
        """Vider toutes les données d'un utilisateur (utile pour les tests)"""
        print(f"🗑️  Suppression des données de l'utilisateur {user_id}")
        return self.db.clear_user_data(user_id)
    
    def get_loading_summary(self, user_id: str) -> dict:
        """Obtenir un résumé des données chargées"""
        return self.db.get_platform_summary(user_id)
    
    def load_specific_pea_files(self, releve_path: str, evaluation_path: str, user_id: str) -> bool:
        """
        Méthode utilitaire pour charger des fichiers PEA spécifiques
        Utile pour les tests et le chargement manuel
        """
        return self.load_pea_data(releve_path, evaluation_path, user_id)
    
    def validate_pea_files(self, releve_path: str = None, evaluation_path: str = None) -> dict:
        """
        Valider les fichiers PEA avant chargement
        
        Returns:
            dict: Résultats de validation avec statut et messages
        """
        validation_result = {
            'valid': True,
            'messages': [],
            'files_found': {}
        }
        
        files_to_validate = []
        if releve_path:
            files_to_validate.append(('releve', releve_path))
        if evaluation_path:
            files_to_validate.append(('evaluation', evaluation_path))
        
        if not files_to_validate:
            validation_result['valid'] = False
            validation_result['messages'].append("Aucun fichier PEA fourni")
            return validation_result
        
        for file_type, file_path in files_to_validate:
            if os.path.exists(file_path):
                # Vérifier que c'est bien un PDF
                if file_path.lower().endswith('.pdf'):
                    try:
                        # Test d'ouverture du PDF
                        import pdfplumber
                        with pdfplumber.open(file_path) as pdf:
                            if len(pdf.pages) > 0:
                                validation_result['files_found'][file_type] = {
                                    'path': file_path,
                                    'pages': len(pdf.pages),
                                    'valid': True
                                }
                                validation_result['messages'].append(f"✅ {file_type.title()} PDF valide ({len(pdf.pages)} pages)")
                            else:
                                validation_result['valid'] = False
                                validation_result['messages'].append(f"❌ {file_type.title()} PDF vide")
                    except Exception as e:
                        validation_result['valid'] = False
                        validation_result['messages'].append(f"❌ {file_type.title()} PDF corrompu: {e}")
                else:
                    validation_result['valid'] = False
                    validation_result['messages'].append(f"❌ {file_type.title()}: Format non-PDF")
            else:
                validation_result['valid'] = False
                validation_result['messages'].append(f"❌ {file_type.title()}: Fichier non trouvé")
        
        return validation_result
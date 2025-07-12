-- ===== SCHÉMA BASE DE DONNÉES CORRIGÉ - PATRIMOINE EXPERT =====
-- Ajout colonne platform dans cash_flows + nouvelles colonnes expert

-- 1. TABLE INVESTMENTS
CREATE TABLE IF NOT EXISTS investments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,  -- LPB, PretUp, BienPreter, Homunity, PEA, Assurance_Vie
    platform_id VARCHAR(100),       -- ID plateforme externe
    investment_type VARCHAR(50) NOT NULL, -- crowdfunding, stocks, bonds, funds
    asset_class VARCHAR(50),         -- real_estate, equity, fixed_income, mixed
    
    -- Informations projet/actif
    project_name VARCHAR(255),
    company_name VARCHAR(255),
    isin VARCHAR(12),               -- Pour PEA/AV (code ISIN)
    
    -- Données financières
    invested_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    annual_rate DECIMAL(5,2),       -- Taux annuel
    duration_months INTEGER,        -- Durée en mois
    capital_repaid DECIMAL(15,2),  -- Capital remboursé
    remaining_capital DECIMAL(15,2), -- Capital restant dû
    monthly_payment DECIMAL(10,2),  -- Mensualité (pour calculs fiscaux)
    
    -- Dates critiques pour TRI
    investment_date DATE,           -- Date réelle d'investissement (pour TRI)
    signature_date DATE,            -- Date signature/souscription
    expected_end_date DATE,         -- Date de fin prévue
    actual_end_date DATE,           -- Date de fin réelle
    
    -- Statuts et indicateurs
    status VARCHAR(50) DEFAULT 'active', -- active, completed, delayed, defaulted, in_procedure
    is_delayed BOOLEAN DEFAULT FALSE,     -- Projet en retard
    is_short_term BOOLEAN DEFAULT FALSE,  -- Immobilisation < 6 mois
    
    -- Métadonnées
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. TABLE CASH_FLOWS
CREATE TABLE IF NOT EXISTS cash_flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investment_id UUID REFERENCES investments(id), -- Clé étrangère (peut être NULL)
    user_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,  -- 🔥 AJOUTÉ: Traçabilité par plateforme
    
    -- Classification du flux
    flow_type VARCHAR(50) NOT NULL,      -- deposit, investment, repayment, interest, dividend, fee, sale, other
    flow_direction VARCHAR(10) NOT NULL, -- in, out
    
    -- Montants avec gestion fiscale expert
    gross_amount DECIMAL(15,2) NOT NULL DEFAULT 0,  -- Montant brut
    net_amount DECIMAL(15,2) NOT NULL DEFAULT 0,    -- Montant net après taxes
    tax_amount DECIMAL(15,2) DEFAULT 0,             -- Montant des taxes
    
    -- Détail pour TRI et analyses
    capital_amount DECIMAL(15,2) DEFAULT 0,         -- Part capital
    interest_amount DECIMAL(15,2) DEFAULT 0,        -- Part intérêts
    
    -- Dates et statut
    transaction_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'completed',          -- completed, pending, failed
    
    -- Descriptions
    description TEXT,
    payment_method VARCHAR(100),
    
    -- Métadonnées
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. TABLE PORTFOLIO_POSITIONS (pour PEA/AV)
CREATE TABLE IF NOT EXISTS portfolio_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,     -- PEA, Assurance_Vie
    
    -- Identification actif
    isin VARCHAR(12),                   -- Code ISIN
    asset_name VARCHAR(255) NOT NULL,   -- Nom de l'actif
    asset_class VARCHAR(50),            -- stock, etf, fund, bond
    
    -- Position actuelle
    quantity DECIMAL(15,6) NOT NULL DEFAULT 0,
    current_price DECIMAL(15,4) DEFAULT 0,
    market_value DECIMAL(15,2) DEFAULT 0,
    portfolio_percentage DECIMAL(5,2) DEFAULT 0,
    
    -- Dates
    valuation_date DATE NOT NULL,
    
    -- Métadonnées
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. TABLE EXPERT_METRICS_CACHE (pour performances)
CREATE TABLE IF NOT EXISTS expert_metrics_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    platform VARCHAR(50),              -- NULL = global
    metric_type VARCHAR(100) NOT NULL, -- tri, capital_en_cours, concentration, etc.
    
    -- Valeurs métriques
    metric_value DECIMAL(15,4),        -- Valeur principale
    metric_percentage DECIMAL(5,2),    -- Valeur en pourcentage
    metric_json JSONB,                 -- Données complexes
    
    -- Métadonnées calcul
    calculation_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    calculation_period_start DATE,
    calculation_period_end DATE,
    
    -- Index pour performances
    UNIQUE(user_id, platform, metric_type)
);

-- 5. Table des objectifs et projections
CREATE TABLE financial_goals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    goal_name VARCHAR(200) NOT NULL,
    goal_type VARCHAR(50), -- 'financial_freedom', 'retirement', 'purchase', 'emergency_fund'
    target_amount DECIMAL(12,2),
    target_date DATE,
    monthly_contribution DECIMAL(10,2),
    expected_return_rate DECIMAL(5,2),
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Table de configuration utilisateur
CREATE TABLE user_preferences (
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    
    -- Profil investisseur
    age INTEGER,
    risk_tolerance VARCHAR(20), -- 'conservative', 'moderate', 'aggressive'
    investment_horizon_years INTEGER,
    
    -- Préférences dashboard
    default_currency VARCHAR(3) DEFAULT 'EUR',
    preferred_allocation JSONB, -- Allocation cible par classe d'actifs
    notification_settings JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. TABLE LIQUIDITY_BALANCES (pour suivre les liquidités par plateforme)
CREATE TABLE liquidity_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    balance_date DATE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, platform, balance_date) -- Une seule entrée par jour et par plateforme
);

-- ===== INDEX POUR PERFORMANCES =====

-- Index principales tables
CREATE INDEX IF NOT EXISTS idx_investments_user_platform ON investments(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_investments_status ON investments(status);
CREATE INDEX IF NOT EXISTS idx_investments_dates ON investments(investment_date, expected_end_date);

CREATE INDEX IF NOT EXISTS idx_cash_flows_user_platform ON cash_flows(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_cash_flows_type_direction ON cash_flows(flow_type, flow_direction);
CREATE INDEX IF NOT EXISTS idx_cash_flows_date ON cash_flows(transaction_date);
CREATE INDEX IF NOT EXISTS idx_cash_flows_investment ON cash_flows(investment_id);

CREATE INDEX IF NOT EXISTS idx_positions_user_platform ON portfolio_positions(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_positions_isin ON portfolio_positions(isin);

CREATE INDEX IF NOT EXISTS idx_metrics_cache_user ON expert_metrics_cache(user_id, platform, metric_type);

CREATE INDEX IF NOT EXISTS idx_liquidity_balances_user_platform ON liquidity_balances(user_id, platform, balance_date);

-- ===== CONTRAINTES =====

-- Contraintes check
ALTER TABLE cash_flows ADD CONSTRAINT chk_flow_direction 
    CHECK (flow_direction IN ('in', 'out'));

ALTER TABLE cash_flows ADD CONSTRAINT chk_flow_type 
    CHECK (flow_type IN ('deposit', 'withdrawal', 'investment', 'repayment', 'interest', 'dividend', 'fee', 'sale', 'purchase', 'adjustment', 'other'));

ALTER TABLE investments ADD CONSTRAINT chk_investment_status 
    CHECK (status IN ('active', 'completed', 'delayed', 'defaulted', 'in_procedure'));

ALTER TABLE investments ADD CONSTRAINT chk_platform 
    CHECK (platform IN ('La Première Brique', 'PretUp', 'BienPrêter', 'Homunity', 'PEA', 'Assurance_Vie'));

-- ===== FONCTIONS UTILITAIRES =====

-- Fonction mise à jour automatique updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers pour updated_at
CREATE TRIGGER update_investments_updated_at 
    BEFORE UPDATE ON investments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at 
    BEFORE UPDATE ON portfolio_positions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===== VUES POUR ANALYSES RAPIDES =====

-- Vue résumé par plateforme
CREATE OR REPLACE VIEW v_platform_summary AS
SELECT 
    i.user_id,
    i.platform,
    COUNT(*) as nb_investments,
    SUM(i.invested_amount) as total_invested,
    AVG(i.invested_amount) as avg_investment,
    COUNT(CASE WHEN i.status = 'active' THEN 1 END) as active_count,
    COUNT(CASE WHEN i.status = 'completed' THEN 1 END) as completed_count,
    COUNT(CASE WHEN i.is_delayed THEN 1 END) as delayed_count,
    AVG(i.duration_months) as avg_duration_months,
    COUNT(CASE WHEN i.is_short_term THEN 1 END) as short_term_count
FROM investments i
GROUP BY i.user_id, i.platform;

-- Vue flux mensuels
CREATE OR REPLACE VIEW v_monthly_flows AS
SELECT 
    cf.user_id,
    cf.platform,
    DATE_TRUNC('month', cf.transaction_date) as month,
    cf.flow_direction,
    COUNT(*) as nb_flows,
    SUM(cf.gross_amount) as total_gross,
    SUM(cf.net_amount) as total_net,
    SUM(cf.tax_amount) as total_tax
FROM cash_flows cf
GROUP BY cf.user_id, cf.platform, DATE_TRUNC('month', cf.transaction_date), cf.flow_direction;

-- Vue concentration par émetteur
CREATE OR REPLACE VIEW v_concentration_analysis AS
SELECT 
    i.user_id,
    i.platform,
    i.company_name,
    COUNT(*) as nb_projects,
    SUM(i.invested_amount) as total_amount,
    SUM(i.invested_amount) / SUM(SUM(i.invested_amount)) OVER (PARTITION BY i.user_id, i.platform) as share_percentage
FROM investments i
WHERE i.company_name IS NOT NULL
GROUP BY i.user_id, i.platform, i.company_name;

-- ===== SCRIPT DE MIGRATION =====

-- Ajouter la colonne platform si elle n'existe pas
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'cash_flows' AND column_name = 'platform'
    ) THEN
        ALTER TABLE cash_flows ADD COLUMN platform VARCHAR(50);
        
        -- Mise à jour des données existantes basée sur investment_id
        UPDATE cash_flows cf 
        SET platform = i.platform 
        FROM investments i 
        WHERE cf.investment_id = i.id 
        AND cf.platform IS NULL;
        
        -- Pour les flux sans investment_id, deviner la plateforme par description
        UPDATE cash_flows 
        SET platform = CASE 
            WHEN description ILIKE '%LPB%' OR description ILIKE '%première brique%' THEN 'LPB'
            WHEN description ILIKE '%pretup%' THEN 'PretUp'
            WHEN description ILIKE '%bienpreter%' OR description ILIKE '%bien preter%' THEN 'BienPreter'
            WHEN description ILIKE '%homunity%' THEN 'Homunity'
            WHEN description ILIKE '%pea%' OR payment_method = 'PEA' THEN 'PEA'
            WHEN description ILIKE '%assurance%' OR description ILIKE '%av%' THEN 'Assurance_Vie'
            ELSE 'Unknown'
        END
        WHERE platform IS NULL;
        
        -- Rendre la colonne NOT NULL après mise à jour
        ALTER TABLE cash_flows ALTER COLUMN platform SET NOT NULL;
        
        RAISE NOTICE 'Colonne platform ajoutée à cash_flows et données migrées';
    END IF;
END
$$;

-- ===== DONNÉES DE TEST =====

-- Fonction pour générer des données de test
CREATE OR REPLACE FUNCTION generate_test_data(p_user_id UUID DEFAULT '29dec51d-0772-4e3a-8e8f-1fece8fefe0e'::UUID)
RETURNS void AS $$
BEGIN
    -- Supprimer données existantes pour ce user
    DELETE FROM cash_flows WHERE user_id = p_user_id;
    DELETE FROM investments WHERE user_id = p_user_id;
    DELETE FROM portfolio_positions WHERE user_id = p_user_id;
    
    -- Investissement LPB
    INSERT INTO investments (user_id, platform, investment_type, asset_class, project_name, company_name, 
                           invested_amount, annual_rate, duration_months, investment_date, expected_end_date, status) 
    VALUES (p_user_id, 'LPB', 'crowdfunding', 'real_estate', 'Résidence Les Jardins', 'Promoteur ABC', 
            10000, 8.5, 18, '2023-01-15', '2024-07-15', 'active');
    
    -- Flux LPB
    INSERT INTO cash_flows (user_id, platform, flow_type, flow_direction, gross_amount, net_amount, 
                          transaction_date, description)
    VALUES 
    (p_user_id, 'LPB', 'deposit', 'out', 10000, -10000, '2023-01-10', 'Crédit du compte'),
    (p_user_id, 'LPB', 'repayment', 'in', 500, 350, '2023-07-15', 'Remboursement mensualité');
    
    RAISE NOTICE 'Données de test générées pour user %', p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ===== COMMENTAIRES =====

COMMENT ON TABLE investments IS 'Table principale des investissements avec support multi-plateformes';
COMMENT ON TABLE cash_flows IS 'Flux de trésorerie avec traçabilité par plateforme pour calculs TRI';
COMMENT ON TABLE portfolio_positions IS 'Positions actuelles pour PEA et Assurance Vie';
COMMENT ON TABLE expert_metrics_cache IS 'Cache des métriques calculées pour optimiser les performances';
COMMENT ON TABLE liquidity_balances IS 'Soldes de liquidités par plateforme et par date';


COMMENT ON COLUMN cash_flows.platform IS 'Plateforme source du flux - CRUCIAL pour calculs TRI par plateforme';
COMMENT ON COLUMN cash_flows.gross_amount IS 'Montant brut avant taxes';
COMMENT ON COLUMN cash_flows.net_amount IS 'Montant net après taxes (flat tax 30%)';
COMMENT ON COLUMN cash_flows.tax_amount IS 'Montant des taxes (CSG/CRDS + IR)';

COMMENT ON COLUMN investments.investment_date IS 'Date réelle investissement - UTILISÉE pour calcul TRI';
COMMENT ON COLUMN investments.signature_date IS 'Date signature/souscription - pour suivi administratif';
COMMENT ON COLUMN investments.is_delayed IS 'Indicateur automatique de retard vs expected_end_date';
COMMENT ON COLUMN investments.is_short_term IS 'Immobilisation courte < 6 mois pour analyse liquidité';

-- ===== GRANTS (à adapter selon votre setup) =====

-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO your_app_user;
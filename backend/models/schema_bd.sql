-- 1. Table principale des investissements
CREATE TABLE investments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL, -- 'LBP', 'PretUp', 'BienPreter', 'Homunity', 'PEA', 'AV'
    platform_id VARCHAR(100), -- ID du projet/contrat sur la plateforme
    investment_type VARCHAR(50) NOT NULL, -- 'crowdfunding', 'stocks', 'insurance', 'crypto'
    asset_class VARCHAR(50), -- 'real_estate', 'equity', 'bond', 'alternative'
    
    -- Informations projet/actif
    project_name VARCHAR(200),
    company_name VARCHAR(200),
    sector VARCHAR(100),
    geographic_zone VARCHAR(100),
    
    -- Données financières
    invested_amount DECIMAL(12,2) NOT NULL,
    current_value DECIMAL(12,2),
    annual_rate DECIMAL(5,2), -- Taux annuel %
    duration_months INTEGER,
    
    -- Dates importantes
    investment_date DATE NOT NULL,
    signature_date DATE,
    expected_end_date DATE,
    actual_end_date DATE,
    
    -- Statut
    status VARCHAR(50) NOT NULL, -- 'active', 'completed', 'defaulted', 'delayed', 'in_procedure'
    
    -- Métadonnées
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Table des flux de trésorerie (remboursements, dividendes, etc.)
CREATE TABLE cash_flows (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    investment_id UUID REFERENCES investments(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Type de flux
    flow_type VARCHAR(50) NOT NULL, -- 'repayment', 'dividend', 'interest', 'fee', 'deposit', 'withdrawal'
    flow_direction VARCHAR(10) NOT NULL, -- 'in', 'out'
    
    -- Montants
    gross_amount DECIMAL(12,2) NOT NULL,
    net_amount DECIMAL(12,2) NOT NULL,
    capital_amount DECIMAL(12,2) DEFAULT 0,
    interest_amount DECIMAL(12,2) DEFAULT 0,
    fee_amount DECIMAL(12,2) DEFAULT 0,
    tax_amount DECIMAL(12,2) DEFAULT 0,
    
    -- Date et statut
    transaction_date DATE NOT NULL,
    expected_date DATE,
    status VARCHAR(50) DEFAULT 'completed', -- 'completed', 'pending', 'failed'
    
    -- Informations complémentaires
    description TEXT,
    payment_method VARCHAR(50),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Table des positions PEA/AV (valorisation temps réel)
CREATE TABLE portfolio_positions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    investment_id UUID REFERENCES investments(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Identification actif
    isin VARCHAR(20),
    ticker VARCHAR(20),
    asset_name VARCHAR(200) NOT NULL,
    
    -- Position
    quantity DECIMAL(15,6),
    average_price DECIMAL(12,4),
    current_price DECIMAL(12,4),
    currency VARCHAR(3) DEFAULT 'EUR',
    
    -- Valorisation
    market_value DECIMAL(12,2),
    unrealized_pnl DECIMAL(12,2),
    unrealized_pnl_pct DECIMAL(8,4),
    
    -- Date de valorisation
    valuation_date DATE NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Table des objectifs et projections
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

-- 5. Table de configuration utilisateur
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

-- 6. Index pour optimiser les performances
CREATE INDEX idx_investments_user_platform ON investments(user_id, platform);
CREATE INDEX idx_investments_date ON investments(investment_date);
CREATE INDEX idx_cash_flows_user_date ON cash_flows(user_id, transaction_date);
CREATE INDEX idx_cash_flows_investment ON cash_flows(investment_id);
CREATE INDEX idx_portfolio_positions_user ON portfolio_positions(user_id, valuation_date);

-- 7. RLS (Row Level Security) pour la sécurité
ALTER TABLE investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_flows ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Politiques RLS : chaque utilisateur ne voit que ses données
CREATE POLICY "Users can view own investments" ON investments
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own cash flows" ON cash_flows
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own positions" ON portfolio_positions
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own goals" ON financial_goals
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own preferences" ON user_preferences
    FOR ALL USING (auth.uid() = user_id);

-- 8. Fonction pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_investments_updated_at 
    BEFORE UPDATE ON investments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at 
    BEFORE UPDATE ON user_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===== Script pour DÉSACTIVER temporairement RLS (DÉVELOPPEMENT UNIQUEMENT) =====
-- À exécuter dans l'éditeur SQL de Supabase

-- ⚠️  ATTENTION: Ceci désactive la sécurité au niveau des lignes
-- À utiliser UNIQUEMENT en développement avec des données de test

-- 1. Désactiver RLS sur toutes les tables
ALTER TABLE investments DISABLE ROW LEVEL SECURITY;
ALTER TABLE cash_flows DISABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_positions DISABLE ROW LEVEL SECURITY;
ALTER TABLE financial_goals DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences DISABLE ROW LEVEL SECURITY;

-- 2. Créer un utilisateur de test (optionnel)
-- Insérer un utilisateur de test directement dans auth.users
-- NOTE: En production, utilisez l'authentification Supabase normale

INSERT INTO auth.users (
    id,
    email,
    encrypted_password,
    email_confirmed_at,
    created_at,
    updated_at,
    raw_app_meta_data,
    raw_user_meta_data,
    is_super_admin,
    role
) VALUES (
    '29dec51d-0772-4e3a-8e8f-1fece8fefe0e'::uuid,
    'luc.nazarian@gmail.com',
    crypt('password123', gen_salt('bf')),
    now(),
    now(),
    now(),
    '{"provider": "email", "providers": ["email"]}',
    '{"full_name": "Luc Nazarian"}',
    false,
    'authenticated'
) ON CONFLICT (id) DO NOTHING;

-- 3. Créer les préférences utilisateur par défaut
INSERT INTO user_preferences (
    user_id,
    age,
    risk_tolerance,
    investment_horizon_years,
    default_currency,
    preferred_allocation,
    created_at,
    updated_at
) VALUES (
    '29dec51d-0772-4e3a-8e8f-1fece8fefe0e'::uuid,
    43,
    'moderate',
    20,
    'EUR',
    '{"real_estate": 30, "stocks": 70, "bonds": 0}',
    now(),
    now()
) ON CONFLICT (user_id) DO UPDATE SET
    age = EXCLUDED.age,
    risk_tolerance = EXCLUDED.risk_tolerance,
    updated_at = now();

-- 4. Objectif de liberté financière
INSERT INTO financial_goals (
    user_id,
    goal_name,
    goal_type,
    target_amount,
    target_date,
    monthly_contribution,
    expected_return_rate,
    is_active,
    created_at
) VALUES (
    '29dec51d-0772-4e3a-8e8f-1fece8fefe0e'::uuid,
    'Liberté Financière',
    'financial_freedom',
    500000.00,
    '2045-01-01',
    1500.00,
    8,
    true,
    now()
) ON CONFLICT DO NOTHING;

-- 5. Vérification des données
SELECT 
    'Investments' as table_name, 
    count(*) as row_count,
    count(DISTINCT user_id) as unique_users
FROM investments
WHERE user_id = '29dec51d-0772-4e3a-8e8f-1fece8fefe0e'

UNION ALL

SELECT 
    'Cash Flows' as table_name, 
    count(*) as row_count,
    count(DISTINCT user_id) as unique_users  
FROM cash_flows
WHERE user_id = '29dec51d-0772-4e3a-8e8f-1fece8fefe0e'

UNION ALL

SELECT 
    'User Preferences' as table_name,
    count(*) as row_count,
    count(DISTINCT user_id) as unique_users
FROM user_preferences
WHERE user_id = '29dec51d-0772-4e3a-8e8f-1fece8fefe0e';

-- ===== Pour RÉACTIVER RLS plus tard (PRODUCTION) =====
-- Décommenter et exécuter ces lignes pour réactiver la sécurité

/*
-- Réactiver RLS
ALTER TABLE investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_flows ENABLE ROW LEVEL SECURITY; 
ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Recréer les politiques RLS
CREATE POLICY "Users can view own investments" ON investments
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own cash flows" ON cash_flows
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own positions" ON portfolio_positions
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own goals" ON financial_goals
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own preferences" ON user_preferences
    FOR ALL USING (auth.uid() = user_id);
*/
alter Table investments
    Add Column IF NOT EXISTS capital_repaired numeric; -- 'crowdlending', 'equity_crowdfunding', 'real_estate_crowdfunding', 'crypto', 'stocks', 'bonds', 'insurance', 'other';
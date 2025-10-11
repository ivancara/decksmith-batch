-- ============================================================================
-- SCRIPT OTIMIZADO DO BANCO DE DADOS DECKSMITH
-- Com Sistema Completo de Permissões e Níveis de Usuário
-- Versão: 2024-12-26 OTIMIZADA COM PERMISSÕES
-- ============================================================================

-- ============================================================================
-- SEÇÃO 1: LIMPEZA COMPLETA
-- ============================================================================
-- Script to safely remove decksmith_user role
-- ============================================================================
-- SEÇÃO 1: LIMPEZA COMPLETA
-- ============================================================================

-- Script to safely remove roles and drop all objects
DO $$
BEGIN
    -- Check and reassign ownership for decksmith_user
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'decksmith_user') THEN
        REASSIGN OWNED BY decksmith_user TO postgres;
        DROP OWNED BY decksmith_user CASCADE;
    END IF;
    
    -- Check and reassign ownership for decksmith_read_user
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'decksmith_read_user') THEN
        REASSIGN OWNED BY decksmith_read_user TO postgres;
        DROP OWNED BY decksmith_read_user CASCADE;
    END IF;
    
    -- Check and reassign ownership for decksmith_crud_user
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'decksmith_crud_user') THEN
        REASSIGN OWNED BY decksmith_crud_user TO postgres;
        DROP OWNED BY decksmith_crud_user CASCADE;
    END IF;
END
$$;

-- Terminate any active connections to the database
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'decksmith' AND pid <> pg_backend_pid();

-- Drop roles if they exist
DROP ROLE IF EXISTS decksmith_user;
DROP ROLE IF EXISTS decksmith_read_user;
DROP ROLE IF EXISTS decksmith_crud_user;

-- ============================================================================
-- DROP DE TODAS AS TABELAS, VIEWS, FUNÇÕES E EXTENSÕES
-- ============================================================================

-- Drop views (ordem importante: views dependentes primeiro)
DROP VIEW IF EXISTS recent_recommendations CASCADE;
DROP VIEW IF EXISTS public_decks CASCADE;
DROP VIEW IF EXISTS card_popularity CASCADE;
DROP VIEW IF EXISTS decks_with_privacy CASCADE;
DROP VIEW IF EXISTS users_with_permissions CASCADE;

-- Drop tables (ordem importante: dependentes primeiro)
DROP TABLE IF EXISTS api_cache CASCADE;
DROP TABLE IF EXISTS system_logs CASCADE;
DROP TABLE IF EXISTS user_analytics CASCADE;
DROP TABLE IF EXISTS card_synergies CASCADE;
DROP TABLE IF EXISTS recommendations CASCADE;
DROP TABLE IF EXISTS ml_models CASCADE;
DROP TABLE IF EXISTS deck_tags CASCADE;
DROP TABLE IF EXISTS tags CASCADE;
DROP TABLE IF EXISTS deck_matches CASCADE;
DROP TABLE IF EXISTS deck_shares CASCADE;
DROP TABLE IF EXISTS deck_comments CASCADE;
DROP TABLE IF EXISTS deck_likes CASCADE;
DROP TABLE IF EXISTS deck_cards CASCADE;
DROP TABLE IF EXISTS decks CASCADE;
DROP TABLE IF EXISTS card_legalities CASCADE;
DROP TABLE IF EXISTS cards CASCADE;
DROP TABLE IF EXISTS card_sets CASCADE;
DROP TABLE IF EXISTS game_formats CASCADE;
DROP TABLE IF EXISTS user_friendships CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS user_plan_permissions CASCADE;
DROP TABLE IF EXISTS permissions CASCADE;
DROP TABLE IF EXISTS privacy_levels CASCADE;
DROP TABLE IF EXISTS user_plans CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS user_has_permission(INTEGER, VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS update_user_counters() CASCADE;
DROP FUNCTION IF EXISTS update_deck_stats() CASCADE;
DROP FUNCTION IF EXISTS normalize_text(text) CASCADE;
DROP FUNCTION IF EXISTS update_timestamp() CASCADE;

-- Drop extensions (apenas se não estão sendo usadas por outros bancos)
DROP EXTENSION IF EXISTS unaccent CASCADE;
DROP EXTENSION IF EXISTS pg_trgm CASCADE;
DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;
DROP EXTENSION IF EXISTS plpgsql CASCADE;

-- ============================================================================
-- SEÇÃO 2: CRIAÇÃO DO BANCO E USUÁRIOS
-- ============================================================================

CREATE ROLE decksmith_user WITH LOGIN NOSUPERUSER INHERIT NOCREATEROLE CREATEDB NOREPLICATION 
    CONNECTION LIMIT -1 PASSWORD 'Pw#b558c5c2@3419!fa1f58$6642';

CREATE ROLE decksmith_read_user WITH LOGIN NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB NOREPLICATION 
    CONNECTION LIMIT -1 PASSWORD 'Rd#67ec0d6f%885B&94863c*3916';

CREATE ROLE decksmith_crud_user WITH LOGIN NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB NOREPLICATION 
    CONNECTION LIMIT -1 PASSWORD 'Cr#6fdd3607^7ECF(064d33)4402';

-- ============================================================================
-- SEÇÃO 3: EXTENSÕES
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS plpgsql;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ============================================================================
-- SEÇÃO 4: FUNÇÕES UTILITÁRIAS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION normalize_text(input_text text)
RETURNS text AS $$
BEGIN
    RETURN LOWER(TRIM(unaccent(input_text)));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Função para verificar permissões do usuário
CREATE OR REPLACE FUNCTION user_has_permission(user_id_param INTEGER, permission_name VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    has_permission BOOLEAN := false;
BEGIN
    SELECT EXISTS(
        SELECT 1 
        FROM users u
        JOIN user_plan_permissions upp ON u.user_plan_id = upp.user_plan_id
        JOIN permissions p ON upp.permission_id = p.id
        WHERE u.id = user_id_param 
        AND p.name = permission_name
        AND u.is_active = true
        AND p.is_active = true
    ) INTO has_permission;
    
    RETURN has_permission;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SEÇÃO 5: SISTEMA DE PERMISSÕES E PLANOS
-- ============================================================================

-- Tabela de planos de usuário
CREATE TABLE user_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    price_monthly DECIMAL(10,2) DEFAULT 0.00,
    price_yearly DECIMAL(10,2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de permissões do sistema
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL, -- deck, recommendation, admin, social
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de permissões por plano (many-to-many)
CREATE TABLE user_plan_permissions (
    id SERIAL PRIMARY KEY,
    user_plan_id INTEGER REFERENCES user_plans(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    limit_value INTEGER, -- valor limite para permissões quantitativas (ex: max_decks)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT user_plan_permissions_unique UNIQUE (user_plan_id, permission_id)
);

-- Tabela de níveis de privacidade
CREATE TABLE privacy_levels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    can_view_public BOOLEAN DEFAULT true,
    can_view_friends BOOLEAN DEFAULT false,
    can_view_private BOOLEAN DEFAULT false,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SEÇÃO 6: TABELAS CORE - USUÁRIOS E AUTENTICAÇÃO
-- ============================================================================

-- Tabela de usuários (atualizada com sistema de permissões)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(320) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    username VARCHAR(50) UNIQUE,
    google_id VARCHAR(255) UNIQUE,
    avatar_url TEXT,
    user_plan_id INTEGER REFERENCES user_plans(id) DEFAULT 1, -- padrão: free
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    is_admin BOOLEAN DEFAULT false, -- flag especial para admins
    
    -- Contadores de uso mensal (resetados todo mês)
    monthly_recommendations_used INTEGER DEFAULT 0,
    monthly_decks_created INTEGER DEFAULT 0,
    monthly_api_calls INTEGER DEFAULT 0,
    monthly_reset_date DATE DEFAULT CURRENT_DATE,
    
    -- Estatísticas totais
    total_decks_created INTEGER DEFAULT 0,
    total_recommendations_received INTEGER DEFAULT 0,
    last_login_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de sessões de usuário
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(512) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de configurações do usuário
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    theme VARCHAR(20) DEFAULT 'light',
    language VARCHAR(10) DEFAULT 'pt-BR',
    email_notifications BOOLEAN DEFAULT true,
    push_notifications BOOLEAN DEFAULT true,
    default_deck_privacy_id INTEGER REFERENCES privacy_levels(id) DEFAULT 1,
    favorite_formats TEXT[],
    recommendation_settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de amizades entre usuários
CREATE TABLE user_friendships (
    id SERIAL PRIMARY KEY,
    requester_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    addressee_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending', -- pending, accepted, blocked
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT user_friendships_unique UNIQUE (requester_id, addressee_id),
    CONSTRAINT user_friendships_no_self CHECK (requester_id != addressee_id)
);

-- ============================================================================
-- SEÇÃO 7: TABELAS CORE - CARTAS E METADADOS
-- ============================================================================

-- Formatos de jogo
CREATE TABLE game_formats (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sets/Edições
CREATE TABLE card_sets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    set_type VARCHAR(50),
    release_date DATE,
    block_name VARCHAR(255),
    is_online_only BOOLEAN DEFAULT false,
    total_cards INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cartas (tabela principal unificada)
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    name_normalized TEXT GENERATED ALWAYS AS (normalize_text(name)) STORED,
    mana_cost VARCHAR(100),
    converted_mana_cost INTEGER,
    type_line VARCHAR(255),
    oracle_text TEXT,
    flavor_text TEXT,
    power VARCHAR(10),
    toughness VARCHAR(10),
    loyalty VARCHAR(10),
    colors TEXT[],
    color_identity TEXT[],
    rarity VARCHAR(20),
    set_id INTEGER REFERENCES card_sets(id),
    collector_number VARCHAR(20),
    artist VARCHAR(255),
    image_url TEXT,
    price_usd DECIMAL(10,2),
    price_updated_at TIMESTAMP,
    edhrec_rank INTEGER,
    popularity_score DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT cards_name_set_unique UNIQUE (name, set_id)
);

-- Legalidades das cartas por formato
CREATE TABLE card_legalities (
    id SERIAL PRIMARY KEY,
    card_id UUID REFERENCES cards(id) ON DELETE CASCADE,
    format_id INTEGER REFERENCES game_formats(id),
    status VARCHAR(20) NOT NULL,
    
    CONSTRAINT card_legalities_unique UNIQUE (card_id, format_id)
);

-- ============================================================================
-- SEÇÃO 8: TABELAS CORE - DECKS COM SISTEMA DE PRIVACIDADE
-- ============================================================================

-- Decks do usuário (atualizada com sistema de privacidade)
CREATE TABLE decks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    format_id INTEGER REFERENCES game_formats(id),
    colors TEXT[],
    commander_card_id UUID REFERENCES cards(id),
    
    -- Sistema de privacidade
    privacy_level_id INTEGER REFERENCES privacy_levels(id) DEFAULT 1,
    is_featured BOOLEAN DEFAULT false, -- apenas admins podem marcar como featured
    is_complete BOOLEAN DEFAULT false,
    is_competitive BOOLEAN DEFAULT false,
    
    -- Estatísticas
    total_cards INTEGER DEFAULT 0,
    mainboard_cards INTEGER DEFAULT 0,
    sideboard_cards INTEGER DEFAULT 0,
    estimated_price DECIMAL(10,2) DEFAULT 0,
    avg_cmc DECIMAL(4,2),
    
    -- Métricas de engajamento
    views_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    
    -- Métricas de desempenho
    win_rate DECIMAL(5,2),
    games_played INTEGER DEFAULT 0,
    last_played_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cartas nos decks
CREATE TABLE deck_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID REFERENCES decks(id) ON DELETE CASCADE,
    card_id UUID REFERENCES cards(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1,
    is_commander BOOLEAN DEFAULT false,
    is_sideboard BOOLEAN DEFAULT false,
    category VARCHAR(50),
    board_position INTEGER,
    notes TEXT, -- apenas o dono pode editar
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT deck_cards_unique UNIQUE (deck_id, card_id, is_sideboard),
    CONSTRAINT deck_cards_quantity_positive CHECK (quantity > 0)
);

-- Curtidas nos decks
CREATE TABLE deck_likes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID REFERENCES decks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT deck_likes_unique UNIQUE (deck_id, user_id)
);

-- Comentários nos decks
CREATE TABLE deck_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID REFERENCES decks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES deck_comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_edited BOOLEAN DEFAULT false,
    is_moderated BOOLEAN DEFAULT false, -- admins podem moderar
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Compartilhamentos de deck
CREATE TABLE deck_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID REFERENCES decks(id) ON DELETE CASCADE,
    shared_by_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    shared_to_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    share_type VARCHAR(20) DEFAULT 'link', -- link, direct, social
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Histórico de partidas dos decks
CREATE TABLE deck_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID REFERENCES decks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    opponent_deck_id UUID REFERENCES decks(id) ON DELETE SET NULL,
    format_id INTEGER REFERENCES game_formats(id),
    result VARCHAR(20) NOT NULL,
    duration_minutes INTEGER,
    notes TEXT,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags para categorização
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50),
    color VARCHAR(7),
    is_official BOOLEAN DEFAULT false,
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags dos decks (many-to-many)
CREATE TABLE deck_tags (
    deck_id UUID REFERENCES decks(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    
    PRIMARY KEY (deck_id, tag_id)
);

-- ============================================================================
-- SEÇÃO 9: SISTEMA DE RECOMENDAÇÕES E DEEP LEARNING
-- ============================================================================

-- Modelos de Machine Learning (atualizado para Deep Learning)
CREATE TABLE ml_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    algorithm VARCHAR(50) NOT NULL, -- 'deep_learning', 'neural_network', 'transformer', etc.
    model_type VARCHAR(50) DEFAULT 'classification', -- 'classification', 'regression', 'recommendation'
    architecture JSONB, -- Arquitetura da rede neural
    status VARCHAR(50) DEFAULT 'training',
    accuracy DECIMAL(5,4),
    loss DECIMAL(10,6),
    val_accuracy DECIMAL(5,4),
    val_loss DECIMAL(10,6),
    
    -- Métricas específicas para Deep Learning
    precision_score DECIMAL(5,4),
    recall_score DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    auc_score DECIMAL(5,4),
    
    -- Dados de treinamento
    training_data_size INTEGER,
    validation_data_size INTEGER,
    test_data_size INTEGER,
    training_epochs INTEGER DEFAULT 0,
    batch_size INTEGER DEFAULT 32,
    learning_rate DECIMAL(10,8) DEFAULT 0.001,
    
    -- Configurações do modelo
    hyperparameters JSONB,
    optimizer_config JSONB,
    loss_function VARCHAR(50),
    metrics JSONB,
    
    -- Hardware e performance
    training_time_seconds INTEGER,
    gpu_used BOOLEAN DEFAULT false,
    memory_usage_mb INTEGER,
    model_size_mb DECIMAL(10,2),
    
    -- Versionamento e deployment
    is_active BOOLEAN DEFAULT false,
    is_production BOOLEAN DEFAULT false,
    model_path TEXT,
    weights_path TEXT,
    
    -- Timestamps
    trained_at TIMESTAMP,
    deployed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Histórico de treinamento dos modelos
CREATE TABLE ml_training_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES ml_models(id) ON DELETE CASCADE,
    epoch INTEGER NOT NULL,
    loss DECIMAL(10,6),
    accuracy DECIMAL(5,4),
    val_loss DECIMAL(10,6),
    val_accuracy DECIMAL(5,4),
    learning_rate DECIMAL(10,8),
    batch_size INTEGER,
    training_time_seconds INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT ml_training_history_unique UNIQUE (model_id, epoch)
);

-- Datasets para treinamento
CREATE TABLE ml_datasets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    dataset_type VARCHAR(50) NOT NULL, -- 'card_recommendations', 'deck_analysis', 'price_prediction'
    version VARCHAR(20) DEFAULT '1.0',
    
    -- Estatísticas do dataset
    total_samples INTEGER NOT NULL,
    feature_count INTEGER NOT NULL,
    class_count INTEGER,
    
    -- Divisão dos dados
    train_samples INTEGER,
    validation_samples INTEGER,
    test_samples INTEGER,
    
    -- Metadados
    feature_names JSONB,
    class_names JSONB,
    data_schema JSONB,
    preprocessing_steps JSONB,
    
    -- Caminhos dos arquivos
    file_path TEXT,
    preprocessed_path TEXT,
    
    -- Status
    is_processed BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Features extraídas para ML
CREATE TABLE ml_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_id UUID REFERENCES ml_datasets(id) ON DELETE CASCADE,
    feature_name VARCHAR(100) NOT NULL,
    feature_type VARCHAR(50) NOT NULL, -- 'numerical', 'categorical', 'text', 'embedding'
    data_type VARCHAR(50) NOT NULL, -- 'float', 'int', 'string', 'boolean'
    
    -- Estatísticas da feature
    importance_score DECIMAL(5,4),
    correlation_target DECIMAL(5,4),
    missing_values_count INTEGER DEFAULT 0,
    unique_values_count INTEGER,
    
    -- Para features numéricas
    min_value DECIMAL(15,6),
    max_value DECIMAL(15,6),
    mean_value DECIMAL(15,6),
    std_deviation DECIMAL(15,6),
    
    -- Para features categóricas
    category_distribution JSONB,
    
    -- Transformações aplicadas
    transformations JSONB,
    encoding_method VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings de cartas para Deep Learning
CREATE TABLE card_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_id UUID REFERENCES cards(id) ON DELETE CASCADE,
    model_id UUID REFERENCES ml_models(id) ON DELETE CASCADE,
    embedding_vector DECIMAL(8,6)[] NOT NULL, -- Array de valores do embedding
    embedding_dimension INTEGER NOT NULL,
    embedding_type VARCHAR(50) DEFAULT 'card2vec', -- 'card2vec', 'transformer', 'autoencoder'
    
    -- Metadados do embedding
    confidence_score DECIMAL(5,4),
    vector_norm DECIMAL(10,6),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT card_embeddings_unique UNIQUE (card_id, model_id)
);

-- Embeddings de decks
CREATE TABLE deck_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID REFERENCES decks(id) ON DELETE CASCADE,
    model_id UUID REFERENCES ml_models(id) ON DELETE CASCADE,
    embedding_vector DECIMAL(8,6)[] NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    embedding_type VARCHAR(50) DEFAULT 'deck2vec',
    
    -- Agregação das cartas
    aggregation_method VARCHAR(50) DEFAULT 'mean', -- 'mean', 'sum', 'max', 'attention'
    card_weights JSONB, -- Pesos das cartas na agregação
    
    -- Metadados
    confidence_score DECIMAL(5,4),
    vector_norm DECIMAL(10,6),
    cards_count INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT deck_embeddings_unique UNIQUE (deck_id, model_id)
);

-- Histórico de recomendações (atualizado)
CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    deck_id UUID REFERENCES decks(id) ON DELETE CASCADE,
    model_id UUID REFERENCES ml_models(id),
    
    -- Contexto da recomendação
    recommendation_type VARCHAR(50) DEFAULT 'card_suggestion', -- 'card_suggestion', 'deck_improvement', 'similar_deck'
    request_context JSONB,
    
    -- Resultados
    recommended_cards JSONB NOT NULL,
    recommended_decks JSONB,
    similarity_scores JSONB,
    confidence_scores JSONB,
    
    -- Explicabilidade
    explanation JSONB, -- Explicação das recomendações
    feature_importance JSONB,
    similar_patterns JSONB,
    
    -- Feedback e avaliação
    user_feedback INTEGER CHECK (user_feedback BETWEEN 1 AND 5),
    user_rating DECIMAL(3,2) CHECK (user_rating BETWEEN 0 AND 5),
    cards_added_count INTEGER DEFAULT 0,
    cards_rejected_count INTEGER DEFAULT 0,
    
    -- Performance
    response_time_ms INTEGER,
    model_inference_time_ms INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sinergias entre cartas (melhorada com ML)
CREATE TABLE card_synergies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_a_id UUID REFERENCES cards(id) ON DELETE CASCADE,
    card_b_id UUID REFERENCES cards(id) ON DELETE CASCADE,
    
    -- Pontuações de sinergia
    synergy_score DECIMAL(5,4) NOT NULL,
    ml_predicted_score DECIMAL(5,4), -- Predição do modelo de ML
    manual_score DECIMAL(5,4), -- Pontuação manual de especialistas
    
    -- Tipos de sinergia
    synergy_type VARCHAR(50), -- 'combo', 'support', 'archetype', 'mana_curve'
    synergy_category VARCHAR(50), -- 'mechanical', 'thematic', 'statistical'
    
    -- Evidências
    frequency INTEGER DEFAULT 1, -- Quantas vezes apareceram juntas
    deck_count INTEGER DEFAULT 0, -- Em quantos decks aparecem juntas
    win_rate_together DECIMAL(5,4), -- Taxa de vitória quando juntas
    win_rate_separate DECIMAL(5,4), -- Taxa de vitória separadas
    
    -- Contexto
    format_specific JSONB, -- Sinergias específicas por formato
    archetype_specific JSONB, -- Sinergias específicas por arquétipo
    
    -- Metadados ML
    model_version VARCHAR(50),
    prediction_confidence DECIMAL(5,4),
    feature_contributions JSONB,
    
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT card_synergies_unique UNIQUE (card_a_id, card_b_id),
    CONSTRAINT card_synergies_no_self CHECK (card_a_id != card_b_id)
);

-- Análise de meta-game para ML
CREATE TABLE meta_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    format_id INTEGER REFERENCES game_formats(id),
    analysis_date DATE NOT NULL,
    
    -- Dados agregados do meta
    total_decks_analyzed INTEGER NOT NULL,
    unique_commanders INTEGER,
    unique_cards INTEGER,
    avg_deck_price DECIMAL(10,2),
    avg_cmc DECIMAL(4,2),
    
    -- Top cartas e commanders
    top_cards JSONB, -- Top cartas mais usadas
    top_commanders JSONB, -- Top commanders
    emerging_cards JSONB, -- Cartas em ascensão
    declining_cards JSONB, -- Cartas em declínio
    
    -- Análise de arquétipos
    archetype_distribution JSONB,
    archetype_performance JSONB,
    archetype_trends JSONB,
    
    -- Predições do modelo
    meta_predictions JSONB,
    trend_analysis JSONB,
    recommendation_adjustments JSONB,
    
    -- Metadados
    model_id UUID REFERENCES ml_models(id),
    confidence_score DECIMAL(5,4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT meta_analysis_unique UNIQUE (format_id, analysis_date)
);

-- Logs de performance dos modelos
CREATE TABLE ml_model_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES ml_models(id) ON DELETE CASCADE,
    
    -- Métricas de performance
    inference_time_ms INTEGER NOT NULL,
    memory_usage_mb INTEGER,
    cpu_usage_percent DECIMAL(5,2),
    gpu_usage_percent DECIMAL(5,2),
    
    -- Dados da requisição
    input_size INTEGER, -- Tamanho do input
    output_size INTEGER, -- Tamanho do output
    batch_size INTEGER DEFAULT 1,
    
    -- Contexto
    endpoint VARCHAR(100), -- Endpoint que fez a requisição
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    request_id UUID,
    
    -- Ambiente
    environment VARCHAR(20), -- 'development', 'homologation', 'production'
    server_instance VARCHAR(100),
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Configurações de modelos por ambiente
CREATE TABLE ml_model_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES ml_models(id) ON DELETE CASCADE,
    environment VARCHAR(20) NOT NULL, -- 'development', 'homologation', 'production'
    
    -- Configurações específicas
    batch_size INTEGER DEFAULT 32,
    max_sequence_length INTEGER,
    temperature DECIMAL(3,2) DEFAULT 1.0, -- Para modelos generativos
    top_k INTEGER,
    top_p DECIMAL(3,2),
    
    -- Thresholds
    confidence_threshold DECIMAL(5,4) DEFAULT 0.5,
    similarity_threshold DECIMAL(5,4) DEFAULT 0.7,
    
    -- Rate limiting
    max_requests_per_minute INTEGER DEFAULT 60,
    max_requests_per_hour INTEGER DEFAULT 1000,
    
    -- Recursos
    max_memory_mb INTEGER,
    timeout_seconds INTEGER DEFAULT 30,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT ml_model_configs_unique UNIQUE (model_id, environment)
);

-- ============================================================================
-- SEÇÃO 10: ANALYTICS E LOGS
-- ============================================================================

-- Analytics de uso
CREATE TABLE user_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    session_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Logs do sistema
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    component VARCHAR(100),
    context JSONB,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cache de requests externos
CREATE TABLE api_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    response_data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SEÇÃO 11: ÍNDICES OTIMIZADOS
-- ============================================================================

-- Índices para sistema de permissões
CREATE INDEX idx_users_user_plan_id ON users (user_plan_id);
CREATE INDEX idx_users_is_admin ON users (is_admin) WHERE is_admin = true;
CREATE INDEX idx_user_plan_permissions_plan_id ON user_plan_permissions (user_plan_id);
CREATE INDEX idx_user_plan_permissions_permission_id ON user_plan_permissions (permission_id);

-- Índices para usuários
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_users_google_id ON users (google_id);
CREATE INDEX idx_users_is_active ON users (is_active);

-- Índices para busca de cartas
CREATE INDEX idx_cards_name_normalized ON cards USING GIN (name_normalized gin_trgm_ops);
CREATE INDEX idx_cards_colors ON cards USING GIN (colors);
CREATE INDEX idx_cards_color_identity ON cards USING GIN (color_identity);
CREATE INDEX idx_cards_type_line ON cards USING GIN (to_tsvector('portuguese', type_line));
CREATE INDEX idx_cards_cmc ON cards (converted_mana_cost);
CREATE INDEX idx_cards_rarity ON cards (rarity);
CREATE INDEX idx_cards_popularity ON cards (popularity_score DESC);

-- Índices para decks
CREATE INDEX idx_decks_user_id ON decks (user_id);
CREATE INDEX idx_decks_format_id ON decks (format_id);
CREATE INDEX idx_decks_privacy_level_id ON decks (privacy_level_id);
CREATE INDEX idx_decks_colors ON decks USING GIN (colors);
CREATE INDEX idx_decks_featured ON decks (is_featured) WHERE is_featured = true;
CREATE INDEX idx_decks_created_at ON decks (created_at DESC);
CREATE INDEX idx_decks_views ON decks (views_count DESC);
CREATE INDEX idx_decks_likes ON decks (likes_count DESC);

-- Índices para deck_cards
CREATE INDEX idx_deck_cards_deck_id ON deck_cards (deck_id);
CREATE INDEX idx_deck_cards_card_id ON deck_cards (card_id);
CREATE INDEX idx_deck_cards_commander ON deck_cards (is_commander) WHERE is_commander = true;

-- Índices para sistema social
CREATE INDEX idx_deck_likes_deck_id ON deck_likes (deck_id);
CREATE INDEX idx_deck_likes_user_id ON deck_likes (user_id);
CREATE INDEX idx_deck_comments_deck_id ON deck_comments (deck_id);
CREATE INDEX idx_deck_comments_user_id ON deck_comments (user_id);
CREATE INDEX idx_user_friendships_requester ON user_friendships (requester_id);
CREATE INDEX idx_user_friendships_addressee ON user_friendships (addressee_id);
CREATE INDEX idx_user_friendships_status ON user_friendships (status);

-- Índices para recomendações e ML
CREATE INDEX idx_ml_models_status ON ml_models (status);
CREATE INDEX idx_ml_models_is_active ON ml_models (is_active) WHERE is_active = true;
CREATE INDEX idx_ml_models_is_production ON ml_models (is_production) WHERE is_production = true;
CREATE INDEX idx_ml_models_algorithm ON ml_models (algorithm);
CREATE INDEX idx_ml_models_accuracy ON ml_models (accuracy DESC);
CREATE INDEX idx_ml_models_created_at ON ml_models (created_at DESC);

CREATE INDEX idx_ml_training_history_model_id ON ml_training_history (model_id);
CREATE INDEX idx_ml_training_history_epoch ON ml_training_history (model_id, epoch);

CREATE INDEX idx_ml_datasets_type ON ml_datasets (dataset_type);
CREATE INDEX idx_ml_datasets_is_active ON ml_datasets (is_active) WHERE is_active = true;
CREATE INDEX idx_ml_datasets_is_processed ON ml_datasets (is_processed);

CREATE INDEX idx_ml_features_dataset_id ON ml_features (dataset_id);
CREATE INDEX idx_ml_features_importance ON ml_features (importance_score DESC);
CREATE INDEX idx_ml_features_type ON ml_features (feature_type);

CREATE INDEX idx_card_embeddings_card_id ON card_embeddings (card_id);
CREATE INDEX idx_card_embeddings_model_id ON card_embeddings (model_id);
CREATE INDEX idx_card_embeddings_type ON card_embeddings (embedding_type);

CREATE INDEX idx_deck_embeddings_deck_id ON deck_embeddings (deck_id);
CREATE INDEX idx_deck_embeddings_model_id ON deck_embeddings (model_id);
CREATE INDEX idx_deck_embeddings_type ON deck_embeddings (embedding_type);

CREATE INDEX idx_recommendations_user_id ON recommendations (user_id);
CREATE INDEX idx_recommendations_deck_id ON recommendations (deck_id);
CREATE INDEX idx_recommendations_model_id ON recommendations (model_id);
CREATE INDEX idx_recommendations_type ON recommendations (recommendation_type);
CREATE INDEX idx_recommendations_created_at ON recommendations (created_at DESC);
CREATE INDEX idx_recommendations_feedback ON recommendations (user_feedback) WHERE user_feedback IS NOT NULL;

CREATE INDEX idx_card_synergies_card_a ON card_synergies (card_a_id);
CREATE INDEX idx_card_synergies_card_b ON card_synergies (card_b_id);
CREATE INDEX idx_card_synergies_score ON card_synergies (synergy_score DESC);
CREATE INDEX idx_card_synergies_ml_score ON card_synergies (ml_predicted_score DESC);
CREATE INDEX idx_card_synergies_type ON card_synergies (synergy_type);
CREATE INDEX idx_card_synergies_frequency ON card_synergies (frequency DESC);

CREATE INDEX idx_meta_analysis_format_date ON meta_analysis (format_id, analysis_date DESC);
CREATE INDEX idx_meta_analysis_model_id ON meta_analysis (model_id);

CREATE INDEX idx_ml_performance_model_id ON ml_model_performance (model_id);
CREATE INDEX idx_ml_performance_timestamp ON ml_model_performance (timestamp DESC);
CREATE INDEX idx_ml_performance_environment ON ml_model_performance (environment);
CREATE INDEX idx_ml_performance_inference_time ON ml_model_performance (inference_time_ms);

CREATE INDEX idx_ml_model_configs_model_env ON ml_model_configs (model_id, environment);
CREATE INDEX idx_ml_model_configs_active ON ml_model_configs (is_active) WHERE is_active = true;

-- ============================================================================
-- SEÇÃO 12: TRIGGERS
-- ============================================================================

-- Triggers para updated_at
CREATE TRIGGER tr_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_user_plans_updated_at BEFORE UPDATE ON user_plans FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_cards_updated_at BEFORE UPDATE ON cards FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_decks_updated_at BEFORE UPDATE ON decks FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_user_preferences_updated_at BEFORE UPDATE ON user_preferences FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_deck_comments_updated_at BEFORE UPDATE ON deck_comments FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_user_friendships_updated_at BEFORE UPDATE ON user_friendships FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Função para atualizar estatísticas do deck
CREATE OR REPLACE FUNCTION update_deck_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        UPDATE decks 
        SET 
            total_cards = (
                SELECT COALESCE(SUM(quantity), 0) 
                FROM deck_cards 
                WHERE deck_id = OLD.deck_id AND is_sideboard = false
            ),
            mainboard_cards = (
                SELECT COALESCE(SUM(quantity), 0) 
                FROM deck_cards 
                WHERE deck_id = OLD.deck_id AND is_sideboard = false
            ),
            sideboard_cards = (
                SELECT COALESCE(SUM(quantity), 0) 
                FROM deck_cards 
                WHERE deck_id = OLD.deck_id AND is_sideboard = true
            ),
            estimated_price = (
                SELECT COALESCE(SUM(c.price_usd * dc.quantity), 0)
                FROM deck_cards dc
                JOIN cards c ON dc.card_id = c.id
                WHERE dc.deck_id = OLD.deck_id
            )
        WHERE id = OLD.deck_id;
        RETURN OLD;
    ELSE
        UPDATE decks 
        SET 
            total_cards = (
                SELECT COALESCE(SUM(quantity), 0) 
                FROM deck_cards 
                WHERE deck_id = NEW.deck_id AND is_sideboard = false
            ),
            mainboard_cards = (
                SELECT COALESCE(SUM(quantity), 0) 
                FROM deck_cards 
                WHERE deck_id = NEW.deck_id AND is_sideboard = false
            ),
            sideboard_cards = (
                SELECT COALESCE(SUM(quantity), 0) 
                FROM deck_cards 
                WHERE deck_id = NEW.deck_id AND is_sideboard = true
            ),
            estimated_price = (
                SELECT COALESCE(SUM(c.price_usd * dc.quantity), 0)
                FROM deck_cards dc
                JOIN cards c ON dc.card_id = c.id
                WHERE dc.deck_id = NEW.deck_id
            )
        WHERE id = NEW.deck_id;
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_deck_cards_update_stats 
    AFTER INSERT OR UPDATE OR DELETE ON deck_cards 
    FOR EACH ROW EXECUTE FUNCTION update_deck_stats();

-- Função para atualizar contadores do usuário
CREATE OR REPLACE FUNCTION update_user_counters()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        UPDATE users 
        SET total_decks_created = (SELECT COUNT(*) FROM decks WHERE user_id = OLD.user_id)
        WHERE id = OLD.user_id;
        RETURN OLD;
    ELSE
        UPDATE users 
        SET total_decks_created = (SELECT COUNT(*) FROM decks WHERE user_id = NEW.user_id)
        WHERE id = NEW.user_id;
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_decks_update_user_counters 
    AFTER INSERT OR DELETE ON decks 
    FOR EACH ROW EXECUTE FUNCTION update_user_counters();

-- ============================================================================
-- SEÇÃO 13: VIEWS OTIMIZADAS COM SISTEMA DE PERMISSÕES
-- ============================================================================

-- View para usuários com informações de plano e permissões
CREATE VIEW users_with_permissions AS
SELECT 
    u.id,
    u.email,
    u.name,
    u.username,
    u.is_active,
    u.is_admin,
    up.name as plan_name,
    up.display_name as plan_display_name,
    up.price_monthly,
    array_agg(DISTINCT p.name ORDER BY p.name) as permissions,
    u.monthly_recommendations_used,
    COALESCE(upp_rec.limit_value, 0) as monthly_recommendations_limit,
    u.total_decks_created,
    COALESCE(upp_deck.limit_value, 999999) as max_decks_allowed,
    u.created_at
FROM users u
JOIN user_plans up ON u.user_plan_id = up.id
LEFT JOIN user_plan_permissions upp ON up.id = upp.user_plan_id
LEFT JOIN permissions p ON upp.permission_id = p.id
LEFT JOIN user_plan_permissions upp_rec ON up.id = upp_rec.user_plan_id 
    AND EXISTS(SELECT 1 FROM permissions p2 WHERE p2.id = upp_rec.permission_id AND p2.name = 'monthly_recommendations')
LEFT JOIN user_plan_permissions upp_deck ON up.id = upp_deck.user_plan_id 
    AND EXISTS(SELECT 1 FROM permissions p3 WHERE p3.id = upp_deck.permission_id AND p3.name = 'max_decks')
WHERE u.is_active = true
GROUP BY u.id, u.email, u.name, u.username, u.is_active, u.is_admin, 
         up.name, up.display_name, up.price_monthly, u.monthly_recommendations_used,
         upp_rec.limit_value, u.total_decks_created, upp_deck.limit_value, u.created_at;

-- View para decks com controle de privacidade
CREATE VIEW decks_with_privacy AS
SELECT 
    d.id,
    d.name,
    d.description,
    d.user_id,
    u.name as user_name,
    u.username,
    d.format_id,
    gf.name as format_name,
    d.colors,
    d.total_cards,
    d.estimated_price,
    d.views_count,
    d.likes_count,
    d.comments_count,
    pl.name as privacy_level,
    pl.display_name as privacy_display,
    pl.can_view_public,
    pl.can_view_friends,
    pl.can_view_private,
    cmd.name as commander_name,
    d.created_at,
    d.updated_at
FROM decks d
JOIN users u ON d.user_id = u.id
LEFT JOIN game_formats gf ON d.format_id = gf.id
LEFT JOIN privacy_levels pl ON d.privacy_level_id = pl.id
LEFT JOIN cards cmd ON d.commander_card_id = cmd.id
WHERE u.is_active = true;

-- View para popularidade de cartas
CREATE VIEW card_popularity AS
SELECT 
    c.id,
    c.name,
    c.type_line,
    c.colors,
    c.rarity,
    COUNT(dc.deck_id) as deck_count,
    SUM(dc.quantity) as total_quantity,
    AVG(dc.quantity) as avg_quantity,
    COUNT(DISTINCT dc.deck_id) as unique_decks,
    COUNT(DISTINCT d.user_id) as unique_users
FROM cards c
JOIN deck_cards dc ON c.id = dc.card_id
JOIN decks d ON dc.deck_id = d.id
JOIN privacy_levels pl ON d.privacy_level_id = pl.id
WHERE pl.can_view_public = true
GROUP BY c.id, c.name, c.type_line, c.colors, c.rarity
ORDER BY deck_count DESC;

-- View para decks públicos com estatísticas
CREATE VIEW public_decks AS
SELECT 
    d.id,
    d.name,
    d.description,
    d.user_id,
    u.name as user_name,
    u.username,
    d.format_id,
    gf.name as format_name,
    d.colors,
    d.total_cards,
    d.estimated_price,
    d.likes_count,
    d.views_count,
    d.win_rate,
    cmd.name as commander_name,
    array_agg(DISTINCT t.name) as tags,
    d.created_at,
    d.updated_at
FROM decks d
JOIN users u ON d.user_id = u.id
JOIN privacy_levels pl ON d.privacy_level_id = pl.id
LEFT JOIN game_formats gf ON d.format_id = gf.id
LEFT JOIN cards cmd ON d.commander_card_id = cmd.id
LEFT JOIN deck_tags dt ON d.id = dt.deck_id
LEFT JOIN tags t ON dt.tag_id = t.id
WHERE pl.can_view_public = true AND u.is_active = true
GROUP BY d.id, d.name, d.description, d.user_id, u.name, u.username,
         d.format_id, gf.name, d.colors, d.total_cards, d.estimated_price,
         d.likes_count, d.views_count, d.win_rate, cmd.name, d.created_at, d.updated_at
ORDER BY d.created_at DESC;

-- View para recomendações recentes (atualizada)
CREATE VIEW recent_recommendations AS
SELECT 
    r.id,
    r.user_id,
    u.name as user_name,
    r.deck_id,
    d.name as deck_name,
    r.model_id,
    m.name as model_name,
    m.algorithm,
    r.recommendation_type,
    r.confidence_scores,
    r.user_feedback,
    r.user_rating,
    r.cards_added_count,
    r.response_time_ms,
    r.created_at,
    jsonb_array_length(r.recommended_cards) as cards_recommended,
    CASE 
        WHEN r.user_feedback >= 4 THEN 'positive'
        WHEN r.user_feedback = 3 THEN 'neutral'
        WHEN r.user_feedback <= 2 THEN 'negative'
        ELSE 'no_feedback'
    END as feedback_category
FROM recommendations r
JOIN users u ON r.user_id = u.id
LEFT JOIN decks d ON r.deck_id = d.id
LEFT JOIN ml_models m ON r.model_id = m.id
ORDER BY r.created_at DESC;

-- View para performance dos modelos
CREATE VIEW ml_model_performance_summary AS
SELECT 
    m.id,
    m.name,
    m.algorithm,
    m.model_type,
    m.status,
    m.is_active,
    m.is_production,
    m.accuracy,
    m.precision_score,
    m.recall_score,
    m.f1_score,
    m.training_epochs,
    m.batch_size,
    m.learning_rate,
    m.model_size_mb,
    
    -- Estatísticas de uso
    COUNT(r.id) as total_recommendations,
    AVG(r.response_time_ms) as avg_response_time,
    AVG(r.user_rating) as avg_user_rating,
    COUNT(CASE WHEN r.user_feedback >= 4 THEN 1 END) as positive_feedback_count,
    COUNT(CASE WHEN r.user_feedback <= 2 THEN 1 END) as negative_feedback_count,
    
    -- Performance recente
    AVG(CASE WHEN r.created_at >= NOW() - INTERVAL '7 days' THEN r.response_time_ms END) as recent_avg_response_time,
    AVG(CASE WHEN r.created_at >= NOW() - INTERVAL '7 days' THEN r.user_rating END) as recent_avg_rating,
    
    m.trained_at,
    m.deployed_at,
    m.created_at

FROM ml_models m
LEFT JOIN recommendations r ON m.id = r.model_id
GROUP BY m.id, m.name, m.algorithm, m.model_type, m.status, m.is_active, m.is_production,
         m.accuracy, m.precision_score, m.recall_score, m.f1_score, m.training_epochs,
         m.batch_size, m.learning_rate, m.model_size_mb, m.trained_at, m.deployed_at, m.created_at
ORDER BY m.is_production DESC, m.is_active DESC, m.accuracy DESC;

-- View para análise de sinergias
CREATE VIEW card_synergies_analysis AS
SELECT 
    cs.id,
    ca.name as card_a_name,
    cb.name as card_b_name,
    ca.type_line as card_a_type,
    cb.type_line as card_b_type,
    ca.colors as card_a_colors,
    cb.colors as card_b_colors,
    cs.synergy_score,
    cs.ml_predicted_score,
    cs.manual_score,
    cs.synergy_type,
    cs.synergy_category,
    cs.frequency,
    cs.deck_count,
    cs.win_rate_together,
    cs.win_rate_separate,
    
    -- Diferença de performance
    (cs.win_rate_together - cs.win_rate_separate) as synergy_impact,
    
    -- Confiança na predição
    cs.prediction_confidence,
    
    -- Popularidade das cartas individualmente
    (SELECT COUNT(*) FROM deck_cards dc WHERE dc.card_id = cs.card_a_id) as card_a_usage,
    (SELECT COUNT(*) FROM deck_cards dc WHERE dc.card_id = cs.card_b_id) as card_b_usage,
    
    cs.last_seen,
    cs.created_at

FROM card_synergies cs
JOIN cards ca ON cs.card_a_id = ca.id
JOIN cards cb ON cs.card_b_id = cb.id
WHERE cs.synergy_score > 0.3 -- Apenas sinergias significativas
ORDER BY cs.synergy_score DESC, cs.frequency DESC;

-- ============================================================================
-- SEÇÃO 14: DADOS INICIAIS
-- ============================================================================

-- Planos de usuário
INSERT INTO user_plans (name, display_name, description, price_monthly, price_yearly, sort_order) VALUES
    ('free', 'Gratuito', 'Plano básico gratuito com funcionalidades limitadas', 0.00, 0.00, 1),
    ('premium', 'Premium', 'Plano premium com recursos avançados', 9.99, 99.99, 2),
    ('admin', 'Administrador', 'Acesso administrativo completo', 0.00, 0.00, 999);

-- Permissões do sistema
INSERT INTO permissions (name, display_name, description, category) VALUES
    -- Permissões de deck
    ('create_deck', 'Criar Deck', 'Permissão para criar novos decks', 'deck'),
    ('edit_own_deck', 'Editar Próprio Deck', 'Permissão para editar próprios decks', 'deck'),
    ('delete_own_deck', 'Deletar Próprio Deck', 'Permissão para deletar próprios decks', 'deck'),
    ('create_private_deck', 'Criar Deck Privado', 'Permissão para criar decks privados', 'deck'),
    ('export_deck', 'Exportar Deck', 'Permissão para exportar decks', 'deck'),
    ('max_decks', 'Máximo de Decks', 'Limite máximo de decks que pode criar', 'deck'),
    
    -- Permissões de recomendação
    ('get_recommendation', 'Obter Recomendação', 'Permissão para receber recomendações', 'recommendation'),
    ('monthly_recommendations', 'Recomendações Mensais', 'Limite mensal de recomendações', 'recommendation'),
    ('advanced_filters', 'Filtros Avançados', 'Acesso a filtros avançados nas recomendações', 'recommendation'),
    
    -- Permissões sociais
    ('like_deck', 'Curtir Deck', 'Permissão para curtir decks', 'social'),
    ('comment_deck', 'Comentar Deck', 'Permissão para comentar em decks', 'social'),
    ('share_deck', 'Compartilhar Deck', 'Permissão para compartilhar decks', 'social'),
    ('add_friend', 'Adicionar Amigo', 'Permissão para adicionar amigos', 'social'),
    
    -- Permissões administrativas
    ('moderate_content', 'Moderar Conteúdo', 'Permissão para moderar comentários e decks', 'admin'),
    ('manage_users', 'Gerenciar Usuários', 'Permissão para gerenciar usuários', 'admin'),
    ('feature_deck', 'Destacar Deck', 'Permissão para marcar decks como destaque', 'admin'),
    ('view_analytics', 'Ver Analytics', 'Acesso ao painel de analytics', 'admin'),
    ('manage_system', 'Gerenciar Sistema', 'Acesso completo ao sistema', 'admin');

-- Permissões para plano FREE
INSERT INTO user_plan_permissions (user_plan_id, permission_id, limit_value) VALUES
    (1, (SELECT id FROM permissions WHERE name = 'create_deck'), NULL),
    (1, (SELECT id FROM permissions WHERE name = 'edit_own_deck'), NULL),
    (1, (SELECT id FROM permissions WHERE name = 'delete_own_deck'), NULL),
    (1, (SELECT id FROM permissions WHERE name = 'max_decks'), 5),
    (1, (SELECT id FROM permissions WHERE name = 'get_recommendation'), NULL),
    (1, (SELECT id FROM permissions WHERE name = 'monthly_recommendations'), 10),
    (1, (SELECT id FROM permissions WHERE name = 'like_deck'), NULL),
    (1, (SELECT id FROM permissions WHERE name = 'comment_deck'), NULL),
    (1, (SELECT id FROM permissions WHERE name = 'share_deck'), NULL);

-- Permissões para plano PREMIUM
INSERT INTO user_plan_permissions (user_plan_id, permission_id, limit_value) VALUES
    (2, (SELECT id FROM permissions WHERE name = 'create_deck'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'edit_own_deck'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'delete_own_deck'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'create_private_deck'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'export_deck'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'max_decks'), 999999),
    (2, (SELECT id FROM permissions WHERE name = 'get_recommendation'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'monthly_recommendations'), 100),
    (2, (SELECT id FROM permissions WHERE name = 'advanced_filters'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'like_deck'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'comment_deck'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'share_deck'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'add_friend'), NULL),
    (2, (SELECT id FROM permissions WHERE name = 'view_analytics'), NULL);

-- Permissões para plano ADMIN
INSERT INTO user_plan_permissions (user_plan_id, permission_id, limit_value) 
SELECT 3, id, 999999 FROM permissions;

-- Níveis de privacidade
INSERT INTO privacy_levels (name, display_name, description, can_view_public, can_view_friends, can_view_private, sort_order) VALUES
    ('public', 'Público', 'Visível para todos os usuários', true, true, true, 1),
    ('friends', 'Amigos', 'Visível apenas para amigos', false, true, true, 2),
    ('private', 'Privado', 'Visível apenas para o proprietário', false, false, true, 3);

-- Formatos padrão
INSERT INTO game_formats (name, description) VALUES
    ('Commander', 'Formato multiplayer casual com 100 cartas singleton'),
    ('Standard', 'Formato competitivo com sets recentes'),
    ('Modern', 'Formato competitivo desde 8th Edition'),
    ('Legacy', 'Formato competitivo com quase todas as cartas'),
    ('Vintage', 'Formato competitivo com todas as cartas'),
    ('Pioneer', 'Formato competitivo desde Return to Ravnica'),
    ('Historic', 'Formato digital da Arena'),
    ('Pauper', 'Formato apenas com cartas comuns');

-- Tags iniciais
INSERT INTO tags (name, description, category, is_official) VALUES
    ('Aggro', 'Estratégia agressiva focada em velocidade', 'archetype', true),
    ('Control', 'Estratégia de controle do jogo', 'archetype', true),
    ('Combo', 'Estratégia baseada em combinações', 'archetype', true),
    ('Midrange', 'Estratégia equilibrada', 'archetype', true),
    ('Tribal', 'Deck focado em uma tribo específica', 'theme', true),
    ('Voltron', 'Estratégia de equipar uma criatura', 'strategy', true),
    ('Ramp', 'Acelerar recursos de mana', 'strategy', true),
    ('Burn', 'Causar dano direto', 'strategy', true),
    ('Mill', 'Estratégia de moer cartas', 'strategy', true),
    ('Lifegain', 'Ganhar pontos de vida', 'strategy', true),
    ('Budget', 'Deck com baixo custo', 'budget', true),
    ('Competitive', 'Deck competitivo', 'budget', true),
    ('Casual', 'Deck casual', 'budget', true);

-- ============================================================================
-- SEÇÃO 15: PRIVILÉGIOS
-- ============================================================================

ALTER DATABASE decksmith OWNER TO postgres;

-- Privilégios para decksmith_read_user
GRANT CONNECT ON DATABASE decksmith TO decksmith_read_user;
GRANT USAGE ON SCHEMA public TO decksmith_read_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO decksmith_read_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO decksmith_read_user;

-- Privilégios para decksmith_crud_user
GRANT CONNECT ON DATABASE decksmith TO decksmith_crud_user;
GRANT USAGE ON SCHEMA public TO decksmith_crud_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO decksmith_crud_user;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO decksmith_crud_user;

-- Privilégios padrão
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO decksmith_read_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO decksmith_read_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO decksmith_crud_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO decksmith_crud_user;

-- ============================================================================
-- RESULTADO FINAL
-- ============================================================================

SELECT '✅ BANCO DE DADOS DECKSMITH OTIMIZADO COM SISTEMA COMPLETO DE PERMISSÕES CRIADO!' as status;

-- ============================================================================
-- 📊 RESUMO DAS FUNCIONALIDADES IMPLEMENTADAS:
-- ============================================================================
--
-- 🔥 SISTEMA DE PERMISSÕES:
-- • 3 planos: FREE, PREMIUM, ADMIN
-- • 17 permissões granulares por categoria
-- • Limites quantitativos (max_decks, monthly_recommendations)
-- • Controle de privacidade (público, amigos, privado)
--
-- 👥 GESTÃO DE USUÁRIOS:
-- • Autenticação via Google OAuth
-- • Sistema de amizades
-- • Preferências personalizadas
-- • Contadores automáticos de uso
--
-- 🃏 SISTEMA DE DECKS:
-- • Relacionamento obrigatório user → deck
-- • Controle de privacidade por deck
-- • Sistema social (curtidas, comentários, compartilhamentos)
-- • Estatísticas automáticas (cartas, preço, winrate)
-- • Tags para categorização
--
-- 🤖 SISTEMA DE RECOMENDAÇÕES:
-- • Modelos de Machine Learning
-- • Histórico de recomendações com feedback
-- • Sistema de sinergias entre cartas
-- • Contexto de requisição personalizado
--
-- 📊 ANALYTICS E PERFORMANCE:
-- • 50+ índices otimizados
-- • Views especializadas
-- • Triggers automáticos
-- • Cache de APIs externas
-- • Logs do sistema
--
-- 🔐 REGRAS DE NEGÓCIO:
-- • FREE: 5 decks, 10 recomendações/mês, apenas público
-- • PREMIUM: ilimitado, 100 recomendações/mês, privacidade completa
-- • ADMIN: todos os privilégios + moderação + analytics
--
-- ============================================================================
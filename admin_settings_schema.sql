-- ============================================================================
-- ADMIN SETTINGS TABLE - Sistema de Configurações Administrativas
-- Incluindo versionamento de modelos ML
-- ============================================================================

-- Tabela de configurações administrativas
CREATE TABLE IF NOT EXISTS admin_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value JSONB NOT NULL,
    setting_category VARCHAR(50) NOT NULL DEFAULT 'general',
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    CONSTRAINT admin_settings_key_check CHECK (setting_key ~ '^[a-z0-9_]+$'),
    CONSTRAINT admin_settings_category_check CHECK (setting_category IN (
        'general', 'ml_models', 'data_export', 'batch_processing', 'security'
    ))
);

-- Tabela de versionamento de modelos ML
CREATE TABLE IF NOT EXISTS ml_model_versions (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL, -- 'card_recommendation', 'win_rate_predictor', 'synergy_detector'
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    
    -- Metadados técnicos
    tensorflow_version VARCHAR(20),
    architecture_config JSONB,
    training_config JSONB,
    performance_metrics JSONB,
    
    -- Status e ativação
    status VARCHAR(20) DEFAULT 'trained', -- 'trained', 'validated', 'active', 'deprecated', 'archived'
    is_active BOOLEAN DEFAULT false,
    is_default BOOLEAN DEFAULT false,
    
    -- Auditoria
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    trained_at TIMESTAMP WITH TIME ZONE,
    activated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(100),
    
    -- Tags e descrição
    tags TEXT[],
    description TEXT,
    training_notes TEXT,
    
    CONSTRAINT ml_model_versions_unique UNIQUE (model_name, version),
    CONSTRAINT ml_model_versions_status_check CHECK (status IN (
        'trained', 'validated', 'active', 'deprecated', 'archived'
    )),
    CONSTRAINT ml_model_versions_type_check CHECK (model_type IN (
        'card_recommendation', 'win_rate_predictor', 'synergy_detector'
    )),
    CONSTRAINT ml_model_versions_default_unique UNIQUE (model_type, is_default) 
        DEFERRABLE INITIALLY DEFERRED
);

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_admin_settings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_admin_settings_timestamp
    BEFORE UPDATE ON admin_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_admin_settings_timestamp();

-- Função para ativar um modelo específico
CREATE OR REPLACE FUNCTION activate_ml_model_version(
    p_model_type VARCHAR(50),
    p_version VARCHAR(50)
) RETURNS BOOLEAN AS $$
DECLARE
    v_model_id INTEGER;
BEGIN
    -- Verificar se o modelo existe
    SELECT id INTO v_model_id 
    FROM ml_model_versions 
    WHERE model_type = p_model_type AND version = p_version;
    
    IF v_model_id IS NULL THEN
        RAISE EXCEPTION 'Modelo % versão % não encontrado', p_model_type, p_version;
    END IF;
    
    -- Desativar todos os modelos do mesmo tipo
    UPDATE ml_model_versions 
    SET is_active = false, 
        is_default = false,
        activated_at = NULL
    WHERE model_type = p_model_type;
    
    -- Ativar o modelo específico
    UPDATE ml_model_versions 
    SET is_active = true, 
        is_default = true,
        status = 'active',
        activated_at = CURRENT_TIMESTAMP
    WHERE id = v_model_id;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_admin_settings_category ON admin_settings (setting_category);
CREATE INDEX IF NOT EXISTS idx_admin_settings_key ON admin_settings (setting_key);
CREATE INDEX IF NOT EXISTS idx_admin_settings_active ON admin_settings (is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_ml_model_versions_type ON ml_model_versions (model_type);
CREATE INDEX IF NOT EXISTS idx_ml_model_versions_status ON ml_model_versions (status);
CREATE INDEX IF NOT EXISTS idx_ml_model_versions_active ON ml_model_versions (model_type, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_ml_model_versions_created ON ml_model_versions (created_at DESC);

-- Configurações iniciais do sistema
INSERT INTO admin_settings (setting_key, setting_value, setting_category, description) VALUES
-- Configurações de modelos ML
('ml_models_base_path', '"/app/models"', 'ml_models', 'Caminho base para armazenar modelos ML'),
('ml_models_max_versions_per_type', '10', 'ml_models', 'Número máximo de versões mantidas por tipo de modelo'),
('ml_models_auto_cleanup', 'true', 'ml_models', 'Limpar automaticamente versões antigas'),
('ml_models_backup_enabled', 'true', 'ml_models', 'Fazer backup de modelos ativos'),

-- Configurações de exportação de dados
('data_export_base_path', '"/app/exports"', 'data_export', 'Caminho base para exportações'),
('data_export_format', '"parquet"', 'data_export', 'Formato padrão de exportação (parquet, csv)'),
('data_export_compression', '"snappy"', 'data_export', 'Compressão para arquivos Parquet'),
('data_export_max_file_size_mb', '100', 'data_export', 'Tamanho máximo de arquivo em MB'),

-- Configurações de processamento em lote
('batch_processing_chunk_size', '1000', 'batch_processing', 'Tamanho do chunk para processamento'),
('batch_processing_max_parallel', '4', 'batch_processing', 'Máximo de processos paralelos'),
('batch_processing_timeout_minutes', '30', 'batch_processing', 'Timeout para operações em lote'),

-- Configurações gerais
('system_environment', '"development"', 'general', 'Ambiente do sistema (development, staging, production)'),
('logging_level', '"INFO"', 'general', 'Nível de logging'),
('feature_flags', '{"model_versioning": true, "auto_export": true}', 'general', 'Flags de features ativas')

ON CONFLICT (setting_key) DO UPDATE SET
    setting_value = EXCLUDED.setting_value,
    updated_at = CURRENT_TIMESTAMP;

-- View para listar modelos ativos
CREATE OR REPLACE VIEW active_ml_models AS
SELECT 
    model_type,
    model_name,
    version,
    file_path,
    performance_metrics,
    activated_at,
    description
FROM ml_model_versions
WHERE is_active = true
ORDER BY model_type, activated_at DESC;

-- View para histórico de modelos
CREATE OR REPLACE VIEW ml_models_history AS
SELECT 
    model_type,
    model_name,
    version,
    status,
    performance_metrics->>'accuracy' as accuracy,
    performance_metrics->>'loss' as loss,
    file_size_bytes / 1024 / 1024 as size_mb,
    created_at,
    trained_at,
    activated_at,
    description,
    tags
FROM ml_model_versions
ORDER BY model_type, created_at DESC;
#!/usr/bin/env python3
"""
DeckSmith Batch Processing - Initialization Script
==================================================

Script para inicialização e configuração do ambiente.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Adicionar src ao path para imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.infrastructure.config.config_manager import EnvironmentConfigManager
from src.infrastructure.database.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)


async def check_database_connection():
    """Verifica conexão com banco de dados."""
    try:
        config = EnvironmentConfigManager()
        db = DatabaseConnection(config)
        
        async with db.get_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                print("✅ Conexão com banco de dados OK")
                return True
            else:
                print("❌ Problema na conexão com banco de dados")
                return False
                
    except Exception as e:
        print(f"❌ Erro na conexão com banco: {str(e)}")
        return False


def check_environment_variables():
    """Verifica se variáveis de ambiente estão configuradas."""
    required_vars = [
        "DATABASE_HOST",
        "DATABASE_PORT", 
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        print("💡 Copie .env.example para .env e configure os valores")
        return False
    else:
        print("✅ Variáveis de ambiente configuradas")
        return True


def create_directories():
    """Cria diretórios necessários."""
    directories = [
        "logs",
        "data/exports",
        "models",
        "temp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Diretórios criados")


async def main():
    """Função principal de inicialização."""
    print("🚀 Inicializando DeckSmith Batch Processing")
    print("=" * 50)
    
    # 1. Criar diretórios
    create_directories()
    
    # 2. Verificar variáveis de ambiente
    if not check_environment_variables():
        sys.exit(1)
    
    # 3. Verificar conexão com banco
    if not await check_database_connection():
        sys.exit(1)
    
    print("=" * 50)
    print("✅ Sistema inicializado com sucesso!")
    print("🎯 Execute: python main.py --help para ver opções disponíveis")


if __name__ == "__main__":
    asyncio.run(main())
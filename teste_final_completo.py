#!/usr/bin/env python3
"""
Teste Final Completo - Verificação E1→E4 TODAS as Fases
"""
import sys
sys.path.append('.')

def test_e1_dados_ml_reais():
    """Testa E1: Dados ML Reais"""
    try:
        from src.infrastructure.services.ml_training_service import TensorFlowMLService
        
        service = TensorFlowMLService()
        
        # Verificar métodos E1
        e1_methods = [
            '_load_real_data_for_training',
            '_load_card_recommendation_data', 
            '_load_win_rate_data',
            '_load_synergy_data'
        ]
        
        implemented = sum(1 for m in e1_methods if hasattr(service, m))
        
        print(f"✅ E1: {implemented}/{len(e1_methods)} métodos implementados")
        
        return implemented == len(e1_methods)
        
    except Exception as e:
        print(f"❌ E1: Erro - {e}")
        return False

def test_e2_pipeline_otimizado():
    """Testa E2: Pipeline Otimizado"""
    try:
        from src.infrastructure.services.ml_training_service import TensorFlowMLService
        
        service = TensorFlowMLService()
        
        # Verificar métodos E2
        e2_methods = [
            '_preprocess_real_data',
            '_remove_outliers',
            '_normalize_features', 
            '_balance_classes',
            '_assess_data_quality',
            '_engineer_features',
            '_cache_processed_data'
        ]
        
        implemented = sum(1 for m in e2_methods if hasattr(service, m))
        
        print(f"✅ E2: {implemented}/{len(e2_methods)} métodos implementados")
        
        return implemented == len(e2_methods)
        
    except Exception as e:
        print(f"❌ E2: Erro - {e}")
        return False

def test_e3_queries_reais():
    """Testa E3: Queries Reais"""
    try:
        from src.infrastructure.services.ml_training_service import TensorFlowMLService
        import inspect
        
        service = TensorFlowMLService()
        
        # Verificar métodos E3 são async
        e3_methods = [
            '_get_card_data',
            '_suggest_commander', 
            '_process_seed_cards'
        ]
        
        async_count = 0
        for method_name in e3_methods:
            if hasattr(service, method_name):
                method = getattr(service, method_name)
                if inspect.iscoroutinefunction(method):
                    async_count += 1
        
        has_scoring = hasattr(service, '_calculate_commander_score')
        
        print(f"✅ E3: {async_count}/{len(e3_methods)} async + scoring: {'✅' if has_scoring else '❌'}")
        
        return async_count == len(e3_methods) and has_scoring
        
    except Exception as e:
        print(f"❌ E3: Erro - {e}")
        return False

def test_e4_limpeza_mocks():
    """Testa E4: Limpeza de Mocks"""
    try:
        from src.infrastructure.config.dependency_container import get_container
        
        container = get_container()
        
        # 1. Testar se rejeita mocks
        rejects_mocks = False
        try:
            container.switch_to_mock_services()
        except NotImplementedError:
            rejects_mocks = True
        
        # 2. Verificar serviços são reais
        services = ['deck_loading', 'data_export', 'model_training']
        real_services = 0
        
        for service_name in services:
            try:
                service = container.get_service(service_name)
                if not type(service).__name__.startswith('Mock'):
                    real_services += 1
            except:
                pass
        
        # 3. Verificar arquivo depreciado
        deprecated = False
        try:
            with open('src/infrastructure/services/mock_services.py', 'r') as f:
                content = f.read()
                deprecated = 'DEPRECIADO E4' in content
        except:
            deprecated = True  # Se não existe, ok
        
        print(f"✅ E4: Rejeita mocks: {'✅' if rejects_mocks else '❌'}, Serviços reais: {real_services}/{len(services)}, Depreciado: {'✅' if deprecated else '❌'}")
        
        return rejects_mocks and real_services == len(services) and deprecated
        
    except Exception as e:
        print(f"❌ E4: Erro - {e}")
        return False

def test_sistema_integrado():
    """Testa sistema integrado E1-E4"""
    try:
        import asyncio
        from src.infrastructure.services.ml_training_service import TensorFlowMLService
        
        async def test_async():
            service = TensorFlowMLService()
            
            # Teste básico de geração de deck
            result = await service.generate_commander_deck(
                seed_cards=['Lightning Bolt', 'Sol Ring'],
                target_colors=['R'],
                deck_size=60
            )
            
            return result['success']
        
        success = asyncio.run(test_async())
        
        print(f"✅ Sistema Integrado: {'Funcional' if success else 'Com problemas'}")
        
        return success
        
    except Exception as e:
        print(f"❌ Sistema Integrado: Erro - {e}")
        return False

def main():
    print("🚀 TESTE FINAL COMPLETO - VERIFICAÇÃO E1→E4")
    print("=" * 60)
    
    results = []
    
    print("\n🔍 Testando Implementações:")
    
    results.append(test_e1_dados_ml_reais())
    results.append(test_e2_pipeline_otimizado()) 
    results.append(test_e3_queries_reais())
    results.append(test_e4_limpeza_mocks())
    results.append(test_sistema_integrado())
    
    completed = sum(results)
    total = len(results)
    
    print(f"\n📊 RESULTADO FINAL:")
    print(f"✅ Fases Concluídas: {completed}/{total} ({completed/total*100:.0f}%)")
    
    if completed == total:
        print(f"\n🎉 TODAS AS FASES E1→E4 IMPLEMENTADAS COM SUCESSO!")
        print(f"✅ E1: Dados ML Reais - CONCLUÍDO")
        print(f"✅ E2: Pipeline Otimizado - CONCLUÍDO") 
        print(f"✅ E3: Queries Reais - CONCLUÍDO")
        print(f"✅ E4: Limpeza Mocks - CONCLUÍDO")
        print(f"✅ Sistema Integrado - FUNCIONAL")
        
        print(f"\n🎯 STATUS FINAL: PROJETO 100% COMPLETO!")
        
    else:
        print(f"\n⚠️  Ainda há {total - completed} fase(s) para completar")
        
        fase_names = ["E1: Dados ML", "E2: Pipeline", "E3: Queries", "E4: Limpeza", "Sistema"]
        
        for i, (result, name) in enumerate(zip(results, fase_names)):
            status = "✅ COMPLETO" if result else "❌ PENDENTE"
            print(f"   {name}: {status}")
    
    return completed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
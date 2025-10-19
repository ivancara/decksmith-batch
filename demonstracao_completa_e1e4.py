#!/usr/bin/env python3
"""
Demonstração completa do sistema E1-E4 funcionando
"""
import asyncio
import json
from datetime import datetime
import sys
sys.path.append('.')

async def demonstrar_sistema_completo():
    """Demonstra o sistema E1-E4 em funcionamento completo"""
    print("🎯 DEMONSTRAÇÃO COMPLETA DO SISTEMA E1→E4")
    print("=" * 60)
    
    try:
        # Importar serviço real
        from src.infrastructure.services.ml_training_service import TensorFlowMLService
        
        # Instanciar serviço
        ml_service = TensorFlowMLService()
        
        # 1. Cartas sementes (simulando CSV lido)
        seed_cards = [
            "Lightning Bolt",
            "Sol Ring", 
            "Llanowar Elves",
            "Counterspell",
            "Swords to Plowshares"
        ]
        
        print(f"🃏 Cartas Sementes ({len(seed_cards)}):")
        for card in seed_cards:
            print(f"   • {card}")
        
        # 2. Gerar deck Commander
        print(f"\n🚀 Gerando Deck Commander com Sistema E1-E4...")
        
        start_time = datetime.now()
        result = await ml_service.generate_commander_deck(
            seed_cards=seed_cards,
            target_colors=['W', 'U', 'B', 'R', 'G'],
            deck_size=100
        )
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result['success']:
            print(f"✅ Deck gerado em {duration:.2f}s!")
            
            # 3. Informações do deck
            deck_info = {
                'timestamp': datetime.now().isoformat(),
                'commander': result['commander'],
                'colors': result['colors'],
                'total_cards': result['total_cards'],
                'seed_cards_used': result['seed_cards_used'],
                'generated_cards': result['generated_cards'],
                'generation_method': result['generation_method'],
                'system_version': 'E1-E4_Real_Implementation',
                'validation': result['validation'],
                'deck': result['deck']
            }
            
            print(f"👑 Comandante: {result['commander']}")
            print(f"🎨 Cores: {', '.join(result['colors']) if result['colors'] else 'Incolor'}")
            print(f"📊 Total de Cartas: {result['total_cards']}")
            print(f"🌱 Cartas Sementes Usadas: {result['seed_cards_used']}")
            print(f"🤖 Cartas Geradas: {result['generated_cards']}")
            
            # 4. Salvar deck em JSON
            output_file = "deck_commander_e1e4_completo.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(deck_info, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Deck salvo em: {output_file}")
            
            # 5. Mostrar algumas cartas do deck
            print(f"\n🃏 Primeiras 15 Cartas do Deck:")
            for i, card in enumerate(deck_info['deck']['maindeck'][:15], 1):
                source_icon = {
                    "seed": "🌱",
                    "generated": "🤖", 
                    "filler": "🔧"
                }.get(card['source'], "❓")
                
                cmc_info = f" (CMC: {card.get('cmc', '?')})" if 'cmc' in card else ""
                print(f"   {i:2d}. {source_icon} {card['name']}{cmc_info}")
            
            if len(deck_info['deck']['maindeck']) > 15:
                remaining = len(deck_info['deck']['maindeck']) - 15
                print(f"   ... e mais {remaining} cartas")
            
            # 6. Validação do deck
            validation = result['validation']
            print(f"\n✅ Validação do Deck:")
            print(f"   Válido: {'✅ Sim' if validation['is_valid'] else '❌ Não'}")
            
            if validation.get('warnings'):
                print(f"   Avisos: {len(validation['warnings'])}")
            
            if validation.get('errors'):
                print(f"   Erros: {len(validation['errors'])}")
            
            # 7. Estatísticas
            if validation.get('stats'):
                stats = validation['stats']
                if 'average_cmc' in stats:
                    print(f"   CMC Médio: {stats['average_cmc']:.2f}")
                
                if 'type_distribution' in stats:
                    print(f"\n📈 Distribuição por Tipo:")
                    for card_type, count in sorted(stats['type_distribution'].items()):
                        percentage = (count / result['total_cards']) * 100
                        print(f"   {card_type}: {count} ({percentage:.1f}%)")
            
            print(f"\n🎉 DEMONSTRAÇÃO COMPLETA - SISTEMA E1-E4 FUNCIONAL!")
            return True
            
        else:
            print(f"❌ Erro na geração: {result.get('error', 'Erro desconhecido')}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na demonstração: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(demonstrar_sistema_completo())
    exit(0 if success else 1)
#!/usr/bin/env python3
"""
Script para gerar deck Commander a partir de CSV
"""
import csv
import sys
import subprocess

def read_cards_from_csv(csv_file):
    """Lê cartas de um arquivo CSV"""
    cards = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                card_name = row.get('card_name', '').strip()
                if card_name:
                    cards.append(card_name)
        return cards
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return []

def generate_deck_from_csv(csv_file, output_file=None):
    """Gera deck Commander usando cartas do CSV"""
    print(f"📖 Lendo cartas do arquivo: {csv_file}")
    
    cards = read_cards_from_csv(csv_file)
    if not cards:
        print("❌ Nenhuma carta encontrada no CSV")
        return False
    
    print(f"✅ Encontradas {len(cards)} cartas: {', '.join(cards)}")
    
    # Preparar comando CLI
    seed_cards = ','.join(cards)
    
    cmd = [
        'python', 'cli.py', 'generate-commander-deck',
        '--seed-cards', seed_cards,
        '--deck-size', '100',
        '--show-details'
    ]
    
    if output_file:
        cmd.extend(['--output', output_file])
    
    print(f"🚀 Executando comando: {' '.join(cmd)}")
    
    # Executar comando
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("✅ Deck gerado com sucesso!")
            print(result.stdout)
            return True
        else:
            print(f"❌ Erro na geração: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao executar comando: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python generate_deck_from_csv.py <arquivo.csv> [output.json]")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "deck_gerado.json"
    
    success = generate_deck_from_csv(csv_file, output_file)
    sys.exit(0 if success else 1)
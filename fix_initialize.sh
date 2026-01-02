#!/bin/bash

# Script para atualizar o initialize com Python 3.11

sudo sed -i '' 's|PYTHON_PATH="/opt/homebrew/bin/python3"|PYTHON_PATH="/opt/homebrew/opt/python@3.11/bin/python3.11"|' /usr/local/bin/initialize

# Verifica se a alteração foi aplicada
if grep -q "python3.11" /usr/local/bin/initialize; then
    echo "✅ Script initialize atualizado com sucesso!"
    echo "📋 Verificação:"
    grep "PYTHON_PATH" /usr/local/bin/initialize
else
    echo "❌ Erro ao atualizar o script"
    exit 1
fi


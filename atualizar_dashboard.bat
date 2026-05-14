@echo off
title Tiger CS Dashboard - Atualizador
color 0A
echo.
echo  ===========================================
echo   Tiger CS Dashboard - Atualizador
echo  ===========================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python nao encontrado!
    echo  Instale em: https://www.python.org/downloads/
    echo  Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

REM Instala dependências se necessário
echo  Verificando dependencias...
pip install requests pandas openpyxl --quiet --disable-pip-version-check

echo.
echo  Iniciando atualizacao...
echo.

REM Executa o script na pasta onde o .bat está
cd /d "%~dp0"
python scripts\atualizar_dashboard.py

exit /b 0

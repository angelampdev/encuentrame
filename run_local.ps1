# Carga las variables del archivo .env en esta sesión de terminal
# y arranca la app tal cual (python app.py), sin instalar nada ni tocar el código.

Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        Set-Item -Path "Env:$name" -Value $value
    }
}

python app.py

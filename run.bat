IF EXIST python.exe (
pass
) ELSE (
echo python.exe must be installed and added to PATH (must be version 3)
)

echo TODO: Add requirement checking

cd rogue
python.exe main.py
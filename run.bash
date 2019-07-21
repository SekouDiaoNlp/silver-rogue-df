command -v python3 -c "" >/dev/null 2>&1 || {
 echo >&2 "Python3 must be installed and added to PATH";
 exit 1;
}
all_modules_installed=1
while IFS= read -r line; do
	echo "Checking if $line is installed"
	python3 -c "import $line" > /dev/null 2>&1
	if [ $? -eq 1 ] 
	then
		echo "$line is not pip-installed!"
		all_modules_installed=0
		break
	fi
done < "./requirements.txt"
if [ $all_modules_installed -eq 1 ]  
then
	python3 main.py
fi

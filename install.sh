current_folder=$(pwd)
echo $current_folder
for route in file smartmetadata series teams users workflows workflowstasks templates
do
  tmp="$current_folder/$route"
  echo $tmp
  mkdir $tmp
  ln -s "$current_folder/__main__.py" "$tmp/models.py"
done
{
  pip3 install -r "$current_folder/requirements.txt"
} || {
  pip install -r "$current_folder/requirements.txt"
}

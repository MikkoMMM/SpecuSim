#!/bin/bash
#set -x

trap cleanup SIGHUP SIGINT SIGQUIT SIGABRT

cleanup()
{
  echo "Cleaning up and quitting."
  exit 1
}

while true; do
	ls -lR > ../specusim-activity2.txt
	ls -lR /mnt/lvdata/Projects/tom-suunnitelmia/ > ../specusim-plan-activity2.txt
	ls -lR /mnt/lvdata/Projects/tom > ../specusim-misc-activity2.txt
	diff ../specusim-activity.txt ../specusim-activity2.txt | grep "^>" | cut -c28- | grep -v ".pyc\$" | grep -v " src\$" | sed '/^ *$/d' >> ../file-activity.txt
	diff ../specusim-plan-activity.txt ../specusim-plan-activity2.txt | grep "^>" | cut -c28- | grep -v ".pyc\$" | grep -v " src\$" | sed '/^ *$/d' >> ../file-activity.txt
	diff ../specusim-misc-activity.txt ../specusim-misc-activity2.txt | grep "^>" | cut -c28- | grep -v ".pyc\$" | grep -v " src\$" | sed '/^ *$/d' >> ../file-activity.txt
	mv ../specusim-activity2.txt ../specusim-activity.txt
	mv ../specusim-plan-activity2.txt ../specusim-plan-activity.txt
	mv ../specusim-misc-activity2.txt ../specusim-misc-activity.txt
	sleep 60
done

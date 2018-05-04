ssh $1 'rm -r /tmp/beeper'
ssh $1 'sudo killall python3'
scp -r ./*.py $1:/tmp/
scp -r ./beeper $1:/tmp/
ssh $1 'cd /tmp; sudo python3 run.py'

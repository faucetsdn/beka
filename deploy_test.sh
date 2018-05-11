ssh $1 'rm -r /tmp/beeper'
ssh $1 'sudo killall python3'
scp -rq ./*.py $1:/tmp/
scp -rq ./beeper.yaml $1:/tmp/
scp -rq ./beeper $1:/tmp/
ssh -t $1 'cd /tmp; sudo python3 run.py'

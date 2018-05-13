ssh $1 'rm -r /tmp/beka'
ssh $1 'sudo killall python3'
scp -rq ./*.py $1:/tmp/
scp -rq ./beka.yaml $1:/tmp/
scp -rq ./beka $1:/tmp/
ssh -t $1 'cd /tmp; sudo python3 run.py'

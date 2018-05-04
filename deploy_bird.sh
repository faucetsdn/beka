scp bird.conf $1:/tmp/
#ssh $1 'docker rm $(docker ps -a -q -f "name=bird")'
#ssh $1 'docker rm $(docker ps -a -q)'
# rm /var/run/bird/bird.ctl; bird
ssh $1 'docker stop bird; docker rm bird; docker run --name bird -v /tmp/bird.conf:/etc/bird/bird.conf -d osrg/bird /usr/sbin/bird -d'
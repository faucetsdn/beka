scp bird.conf $1:/tmp/
scp bird6.conf $1:/tmp/
ssh $1 'mkdir /tmp/bird; mkdir /tmp/bird6'
ssh $1 'docker network create --subnet 172.25.0.0/16 --ipv6 --subnet 2001:db9:1::/64 bird-net'
ssh $1 'docker stop bird; docker rm bird; docker run --name bird --network bird-net -v /tmp/bird.conf:/etc/bird/bird.conf -v /tmp/bird:/run/bird --ip 172.25.0.111 -d osrg/bird /usr/sbin/bird -d; sleep 1; docker ps -a'
ssh $1 'docker stop bird6; docker rm bird6; docker run --name bird6 --network bird-net -v /tmp/bird6.conf:/etc/bird/bird6.conf -v /tmp/bird6:/run/bird --ip6 2001:db9:1::99 -d osrg/bird /usr/sbin/bird6 -d; sleep 1; docker ps -a'
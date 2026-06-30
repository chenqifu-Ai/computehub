sleep 5
pkill -f "worker.*local-arm" 2>/dev/null
sleep 5
mv -f /data/data/com.termux/files/home/OPC/ch-v1.3.17 /data/data/com.termux/files/home/OPC/bin/linux-arm64/computehub
nohup /data/data/com.termux/files/home/OPC/bin/linux-arm64/computehub worker --agent --gw http://36.250.122.43:8282 --node-id local-arm --interval 3 --concurrent 8 --heartbeat 10 >/dev/null 2>&1 &
echo DONE

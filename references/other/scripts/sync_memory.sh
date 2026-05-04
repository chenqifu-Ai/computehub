#!/usr/bin/expect -f

set timeout 30
set host "192.168.1.3"
set username "chen"
set password "c9fc9f,."
set local_path "/root/.openclaw/workspace/memory/"
set remote_path "/home/chen/.openclaw/workspace/memory/"

spawn rsync -avz --exclude='node_modules' --exclude='.git' $local_path $username@$host:$remote_path

expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    eof
}
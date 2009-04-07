# /etc/profile.d/s390.sh - set TERM variable

contype=`/sbin/consoletype`
if [ "$contype" == "serial" ]; then
    export TERM=dumb
fi

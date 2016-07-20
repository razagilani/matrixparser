#!/bin/sh
#
# based on:
# https://gist.github.com/shrkw/7247765
#
# chkconfig: - 86 14
# processname: gunicorn
# pidfile: 
# description: Python application server
#
### BEGIN INIT INFO
# Provides: gunicorn_sr
# Required-Start: $local_fs $remote_fs $network
# Required-Stop: $local_fs $remote_fs $network
# Default-Start: 3
# Default-Stop: 0 1 2 4 5 6
# Short-Description: start and stop gunicorn
### END INIT INFO

# Source function library.
. /etc/rc.d/init.d/functions

prog=/home/matrix/matrix-virtualenv/bin/gunicorn
ARGS="--bind 127.0.0.1:8080 -m 0 bin.run_web"
APP_ROOT=/home/matrix/quote-parser/
lockfile=${LOCKFILE-/var/lock/subsys/gunicorn}
pidfile=/var/run/gunicorn_sr.pid
pidfile_old=${pidfile}.oldbin
RETVAL=0


start() {
    echo -n $"Starting $prog: "
    cd $APP_ROOT
    . /home/matrix/matrix-virtualenv/bin/activate
    gunicorn --pid $pidfile --daemon ${ARGS}
    RETVAL=$?
    echo -n
    [ $RETVAL = 0 ] && echo -e '[\e[32m OK \e[m]'
    [ $RETVAL = 0 ] && touch ${lockfile}
    return $RETVAL
}

stop() {
    echo -n $"Stopping $prog: "
    killproc -p ${pidfile} ${prog} -QUIT
    RETVAL=$?
    echo
    [ $RETVAL = 0 ] && rm -f ${lockfile} ${pidfile}
}

restart() {
    echo -n $"Restarting $prog: "
    killproc -p ${pidfile} ${prog} -USR2
    RETVAL=$?
    echo
    echo -n $"Stopping old $prog: "
    killproc -p ${pidfile_old} ${prog} -QUIT
    RETVAL=$?
    echo
}

reload() {
    echo -n $"Reloading $prog: "
    killproc -p ${pidfile} ${prog} -HUP
    RETVAL=$?
    echo
}

rh_status() {
    status -p ${pidfile} ${prog}
}

# See how we were called.
case "$1" in
    start)
        rh_status >/dev/null 2>&1 && exit 0
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    reload)
        reload
        ;;
    condrestart|try-restart)
        if rh_status >/dev/null 2>&1; then
            stop
            start
        fi
        ;;
    status)
        rh_status
        RETVAL=$?
        ;;
    *)
        echo $"Usage: $prog {start|stop|restart|reload|condrestart|try-restart|status|help}"
        RETVAL=2
esac

exit $RETVAL

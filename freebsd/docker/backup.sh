#!/bin/bash

DEFAULT_USER="admin"
DEFAULT_PASSWORD="admin"
BACKUP_FILE="backup.tar.gz"
BACKUP_PATH=/config/$BACKUP_FILE
REMOTE_BACKUP_PATH=/tmp/$BACKUP_FILE

handle_args() {
    # Parse options
    while getopts 'u:p:' OPTION; do
        case "$OPTION" in
            u)
            user="$OPTARG"
            ;;
            p)
            password="$OPTARG"
            ;;
            ?)
            usage
            exit 1
            ;;
        esac
    done
    shift "$(($OPTIND -1))"

    # Assign defaults if options weren't provided
    if [ -z "$user" ] ; then
        user=$DEFAULT_USER
    fi
    if [ -z "$password" ] ; then
        password=$DEFAULT_PASSWORD
    fi
    
    SSH_CMD="sshpass -p $password ssh -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    SCP_CMD="sshpass -p $password scp -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    HOST="$user@localhost"

    # Parse commands
    case $1 in

    backup)
        backup
        ;;

    restore)
        restore
        ;;

    *)
        usage
        ;;
    esac
}

usage() {
	echo "Usage: $(basename $0) [-u USERNAME] [-p PASSWORD] COMMAND"
    echo "Options:"
    echo "  -u USERNAME    VM SSH username (default: admin)"
    echo "  -p PASSWORD    VM SSH password (default: admin)"
    echo
    echo "Commands:"
    echo "  backup         Backup VM /etc directory to $BACKUP_PATH"
    echo "  restore        Restore VM /etc directory from $BACKUP_PATH"
	exit 0;
}

backup() {
    echo "Backing up..."
    $SSH_CMD $HOST "sudo tar zcf $REMOTE_BACKUP_PATH /etc > & /dev/null"
    $SCP_CMD $HOST:$REMOTE_BACKUP_PATH $BACKUP_PATH
}

restore() {
    if [ -f "$BACKUP_PATH" ]; then
        echo "Restoring from backup..."
        # Put backup file to VM, untar, and reboot.
        $SCP_CMD $BACKUP_PATH $HOST:$REMOTE_BACKUP_PATH && $SSH_CMD $HOST "sudo tar xzf $REMOTE_BACKUP_PATH -C /" && $SSH_CMD $HOST "sudo shutdown -r now || true"
    else 
        echo "$BACKUP_PATH not found. Nothing to restore."
    fi
}

handle_args "$@"

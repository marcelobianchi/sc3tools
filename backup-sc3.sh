#!/bin/bash
##################################################################

################################################################################
#                                                                              #
# Dump seiscomp3 database to XML                                               #
# written by Mb @ USP                                                          #
# this is free software                                                        #
#                                                                              #
#### 2015-02-26 ################################################################

function cleanup() {
	rmdir --ignore-fail-on-non-empty ${dir}
}

dir="$(date +%Y%m%d%H%M)"

mkdir -p $dir/

DB="$1" && shift
[ -z "$DB" ] && DB="mysql://sysop:sysop@localhost/seiscomp3" && echo "Using default DB => ${DB}"

#
# Inventory
##
echo -n "Inventory to $dir/Inventory.xml . . . "
seiscomp exec scxmldump -d ${DB} -I -f -o $dir/Inventory.xml $*
[ $? -ne 0 ] && echo "Error." && cleanup && exit 1
echo "done."

#
# Routing
##
echo -n "Routing to $dir/Routing.xml . . . "
seiscomp exec scxmldump -d ${DB} -R -f -o $dir/Routing.xml $*
[ $? -ne 0 ] && echo "Error." && cleanup && exit 1
echo "done."

#
# Config
##
echo -n "Config to $dir/Config.xml . . . "
seiscomp exec scxmldump -d ${DB} -C -f -o $dir/Config.xml $*
[ $? -ne 0 ] && echo "Error." && cleanup && exit 1
echo "done."

#
# Events
##
seiscomp exec scevtls -d ${DB} --begin '1980-01-01 00:00:00' --end "$(( $(date -u +%Y) + 1 ))-01-01 00:00:00" | while read evID
do
	echo -n "Working on $evID . . . "
	seiscomp exec scxmldump -d ${DB} -E ${evID} -P -A -M -F -f -m -o  $dir/$evID.xml
	[ $? -ne 0 ] && echo "Error." && continue
	echo "done."
done

#
# Cleanup
##
cleanup

exit 0

#
# allreduce-bypass.py :- to evaluate mpi_allreduce performance
#

import sys
from ppt import *

def allreduce_app(mpi_comm_world, data_size, pack_size):
    n = mpi_comm_size(mpi_comm_world) 
    p = mpi_comm_rank(mpi_comm_world)
    #print("%d/%d on %s" % (p, n, mpi_ext_host(mpi_comm_world)))

    r = mpi_allreduce(p, mpi_comm_world, data_size)
    if r is None: 
        raise Exception("error occurred in running allreduce")
    t = mpi_wtime(mpi_comm_world)
   
    # we could use another reduce to get the max of all
    #
    #t = mpi_reduce(0, t, mpi_comm_world, op="max")
    #if t is None: 
    #    raise Exception("error occurred in running reduce")
    #if p == 0:
    #    print("%d %d %f (ns)" % (n, data_size, t*1e9))
    #
    # on the other hand, the last process is as good as it goes
    if p == n-1: 
        print("p=%d c=%d %d %f (nanosecs)" % (n, pack_size, data_size, t*1e9))

    # BUG-AND-FIX: simian process when terminates will not context
    # switch back to another running process; to avoid this problem,
    # we require the user mpi process to call mpi_finalize (which
    # actually hibernates the process forever)
    mpi_finalize(mpi_comm_world)

if len(sys.argv) != 4:
    print("Usage: allreduce-bypass.py total_ranks ranks_per_host data_size ")
    sys.exit(1)

n = int(sys.argv[1])
x = int(sys.argv[2]) 
s = int(sys.argv[3])
print("allreduce-bypass.py %d %d %d" % (n, x, s))

modeldict = {
    "model_name" : "allreduce-bypass",
    "sim_time" : 1e9,
    "use_mpi" : True,
    "intercon_type" : "Bypass", # use interconnect bypass
    "bypass" : {
        "nhosts" : n,
        "bdw" : 1e10,
        "link_delay" : 1e-6
    },
    "host_type" : "Host",
    "load_libraries": set(["mpi"]), # load mpi library for the application
    #"mpiopt" : configs.gemini_mpiopt, # mpiopt has no effect for bypass
}
#cluster = Cluster(modeldict, debug_options={"mpi"})
#cluster = Cluster(modeldict)

# there will be ceiling(n/x) number of hosts that will run this
# application (allreduce_app); if simian is run in parallel, we want
# these hosts to be partitioned evenly among the LPs to achieve load
# balance; the parameter 'partition_hosts' is an optional argument to
# Cluster constructor for this purposes: it tells simian how the hosts
# and switches in the cluster are expected to be mapped to the LPs
cluster = Cluster(modeldict, partition_hosts=int((n+x-1)/x))

total_hosts = cluster.num_hosts()
cores_per_host = 24
total_cores = total_hosts*cores_per_host
if n > total_cores:
    print("ERROR: the cluster doesn't have enough cores (%d*%d=%d) to run this job (n=%d)" %
          (total_hosts, cores_per_host, total_cores, n))
    sys.exit(2)

# each compute node has multiple cores; we try to put an mpi process
# on each core and put neighboring processes on the same node if at
# all possible
hostmap = [(i/x)%total_hosts for i in range(n)]
cluster.start_mpi(hostmap, allreduce_app, s, x)

cluster.run()
